import graphene
import graphql_jwt
from graphql_jwt.shortcuts import get_token
from graphql_jwt.refresh_token.shortcuts import create_refresh_token
from graphql_jwt.decorators import login_required
from django.contrib.auth import authenticate

from esi.models import Token
from allianceauth.authentication.models import CharacterOwnership

from .types import UserProfileType
from .errors import UserNotRegisteredError


class EsiTokenAuthMutation(graphene.Mutation):
    """Login Mutation

    Receives the esi code from callback and provides a JWT token for the Authorization header:
    Authorization: JWT <token>
    """
    me = graphene.Field(UserProfileType)
    token = graphene.String()
    refresh_token = graphene.String()

    class Arguments:
        sso_token = graphene.String(required=True, description="The code param received from esi callback")

    @classmethod
    def mutate(cls, root, info, sso_token):
        token_obj = Token.objects.create_from_code(sso_token)
        user = authenticate(token=token_obj)

        if user:
            token_obj.user = user
            if Token.objects.exclude(pk=token_obj.pk).equivalent_to(token_obj).require_valid().exists():
                token_obj.delete()
            else:
                token_obj.save()

            if user.is_active:
                token = get_token(user)
            else:
                raise UserNotRegisteredError('User is not registered. Register to AllianceAuth site first.')

        else:
            raise Exception('Unable to authenticate the selected character')

        token = get_token(user)
        refresh_token = create_refresh_token(user).get_token()

        return cls(me=user.profile, token=token, refresh_token=refresh_token)


class ChangeMainCharacterMutation(graphene.Mutation):
    """Mutation for changing main character, assuming this character has already been added and it's not owned by another user
    """
    class Arguments:
        new_main_character_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)
    me = graphene.Field(UserProfileType)

    @classmethod
    @login_required
    def mutate(cls, root, info, new_main_character_id):
        errors = []
        profile = info.context.user.profile
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
            profile.main_character = co.character
            profile.save(update_fields=['main_character'])

        return cls(ok=ok, errors=errors, me=profile)


class AddCharacterMutation(graphene.Mutation):
    """Mutation for adding a new character to the list of alts.
    Receives the esi code from callback of the character to add.
    """
    class Arguments:
        new_char_sso_token = graphene.String(required=True)

    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)
    me = graphene.Field(UserProfileType)

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

        return cls(ok=ok, me=user.profile, errors=errors)


class Mutation:
    token_auth = EsiTokenAuthMutation.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    change_main_character = ChangeMainCharacterMutation.Field()
    add_character = AddCharacterMutation.Field()
