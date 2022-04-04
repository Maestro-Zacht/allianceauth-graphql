import graphene
import graphql_jwt
from graphql_jwt.shortcuts import get_token
from django.contrib.auth import authenticate

from esi.models import Token

from .types import UserProfileType
from .errors import UserNotRegisteredError


class EsiTokenAuthMutation(graphene.Mutation):
    me = graphene.Field(UserProfileType)
    token = graphene.String()

    class Arguments:
        sso_token = graphene.String(required=True)

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

        return cls(me=user.profile, token=token)


class Mutation(graphene.ObjectType):
    token_auth = EsiTokenAuthMutation.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
