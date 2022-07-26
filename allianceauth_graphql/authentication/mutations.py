import graphene
import graphql_jwt
from graphql_jwt.shortcuts import get_token
from graphql_jwt.refresh_token.shortcuts import create_refresh_token
from graphql_jwt.decorators import login_required
from django.contrib.auth import authenticate
from django.urls import reverse
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings
from graphene_django.forms.mutation import DjangoFormMutation

from esi.models import Token
from allianceauth.authentication.models import CharacterOwnership

from .forms import EmailRegistrationForm
from .types import UserType, LoginStatus

REGISTRATION_SALT = getattr(settings, "REGISTRATION_SALT", "registration")


class EsiTokenAuthMutation(graphene.Mutation):
    """Login Mutation

    Receives the esi code from callback and provides a token:
    in case the status is "LOGIN", the token is for the Authorization header (Authorization: JWT <token>);
    in case the status is "REGISTRATION", the token is for the RegistrationMutation mutation argument.
    """
    me = graphene.Field(UserType)
    token = graphene.String()
    refresh_token = graphene.String()
    errors = graphene.List(graphene.String)
    status = graphene.Field(LoginStatus)

    class Arguments:
        sso_token = graphene.String(required=True, description="The code param received from esi callback")

    @classmethod
    def mutate(cls, root, info, sso_token):
        errors = []
        token_obj = Token.objects.create_from_code(sso_token)
        user = authenticate(token=token_obj)
        status = 0

        if user:
            token_obj.user = user
            if Token.objects.exclude(pk=token_obj.pk).equivalent_to(token_obj).require_valid().exists():
                token_obj.delete()
            else:
                token_obj.save()

            if user.is_active:
                status = 1
            elif not user.email:
                status = 2
                info.context.session.update({'registration_uid': user.pk})
                info.context.session.save()
            else:
                errors.append('Unable to authenticate the selected character')

        else:
            errors.append('Unable to authenticate the selected character')

        if status == 1:
            token = get_token(user)
            refresh_token = create_refresh_token(user).get_token()
        elif status == 2:
            refresh_token = None
            token = signing.dumps(user.pk)
        else:
            token = refresh_token = None

        return cls(
            me=user if status == 1 else None,
            token=token,
            refresh_token=refresh_token,
            errors=errors,
            status=status
        )


class RegistrationMutation(DjangoFormMutation):
    """Email registration

    Receives the token from LoginMutation (if the status is "REGISTRATION") and the email and sends an email with the activation link.
    """
    class Meta:
        form_class = EmailRegistrationForm

    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @classmethod
    def perform_mutate(cls, form, info):
        errors = []
        user_id = signing.loads(form.data['token'])
        email = form.data['email']

        site = getattr(settings, 'REDIRECT_SITE')

        activation_key = signing.dumps([user_id, email], salt=REGISTRATION_SALT)

        full_url = info.context.build_absolute_uri(reverse('allianceauth_graphql:verify_email')) + f"?activation_key={activation_key}"

        send_mail(
            f'Account activation for {site}',
            f"""< p >
            You're receiving this email because someone has entered this email address while registering for an account on {site}
            < /p >

            < p >
            If this was you, please click on the link below to confirm your email address:
            < p >

            < p >
            < a href="{full_url}" > Confirm email address < /a >
            < / p >

            < p >
            If this was not you, it is safe to ignore this email.
            < /p >""",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False
        )

        return cls(ok=True, errors=errors, **form.data)


class ChangeMainCharacterMutation(graphene.Mutation):
    """Mutation for changing main character, assuming this character has already been added and it's not owned by another user
    """
    class Arguments:
        new_main_character_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)
    me = graphene.Field(UserType)

    @classmethod
    @login_required
    def mutate(cls, root, info, new_main_character_id):
        errors = []
        user = info.context.user
        try:
            co = CharacterOwnership.objects.get(character__character_id=new_main_character_id, user=info.context.user)
            ok = True
        except CharacterOwnership.DoesNotExist:
            ok = False
            if not CharacterOwnership.objects.filter(character__character_id=new_main_character_id).exists():
                errors.append("You never added this character")
            else:
                errors.append("You don't own this character")

        if ok:
            user.profile.main_character = co.character
            user.profile.save(update_fields=['main_character'])

        return cls(ok=ok, errors=errors, me=user)


class AddCharacterMutation(graphene.Mutation):
    """Mutation for adding a new character to the list of alts.
    Receives the esi code from callback of the character to add.
    """
    class Arguments:
        new_char_sso_token = graphene.String(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)
    me = graphene.Field(UserType)

    @classmethod
    @login_required
    def mutate(cls, root, info, new_char_sso_token):
        errors = []
        user = info.context.user
        token_obj = Token.objects.create_from_code(new_char_sso_token, user=user)
        if not CharacterOwnership.objects.filter(user=user, character__character_id=token_obj.character_id, owner_hash=token_obj.character_owner_hash).exists():
            errors.append("This character already has an account")
            ok = False
        else:
            ok = True

        return cls(ok=ok, me=user, errors=errors)


class Mutation:
    token_auth = EsiTokenAuthMutation.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    revoke_token = graphql_jwt.Revoke.Field()
    change_main_character = ChangeMainCharacterMutation.Field()
    add_character = AddCharacterMutation.Field()
    email_registration = RegistrationMutation.Field()
