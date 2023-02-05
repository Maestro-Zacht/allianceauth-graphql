import graphene
from graphql_jwt.decorators import login_required
from esi import app_settings
from requests_oauthlib import OAuth2Session

from django.conf import settings
from django.db.models import Value

from allianceauth.eveonline.models import EveCharacter

from .types import GroupType, UserType
from ..eveonline.types import EveCharacterType


DEFAULT_SCOPES = getattr(settings, 'GRAPHQL_LOGIN_SCOPES', ['publicData'])


class Query:
    esi_login_url = graphene.String(scopes=graphene.List(graphene.String, default_value=DEFAULT_SCOPES))
    me = graphene.Field(UserType)
    authentication_user_groups = graphene.List(GroupType)
    authentication_user_characters = graphene.List(EveCharacterType, description="List of the user's alts")

    def resolve_esi_login_url(self, info, scopes):
        oauth = OAuth2Session(
            app_settings.ESI_SSO_CLIENT_ID,
            redirect_uri=app_settings.ESI_SSO_CALLBACK_URL,
            scope=scopes
        )

        redirect_url, state = oauth.authorization_url(app_settings.ESI_OAUTH_LOGIN_URL)

        return redirect_url

    @login_required
    def resolve_me(self, info):
        return info.context.user

    @login_required
    def resolve_authentication_user_groups(self, info):
        groups = info.context.user.groups.all()
        if 'allianceauth.eveonline.autogroups' in settings.INSTALLED_APPS:
            groups = groups\
                .filter(managedalliancegroup__isnull=True)\
                .filter(managedcorpgroup__isnull=True)
        return groups.order_by('name').annotate(status=Value(1))

    @login_required
    def resolve_authentication_user_characters(self, info):
        return (
            EveCharacter.objects
            .filter(character_ownership__user=info.context.user)
            .order_by('character_name')
        )
