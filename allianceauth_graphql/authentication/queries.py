import graphene
from graphql_jwt.decorators import login_required
from esi import app_settings
from requests_oauthlib import OAuth2Session

from django.conf import settings
from django.db.models import Value

from allianceauth.eveonline.models import EveCharacter

from .types import GroupType, UserType
from ..eveonline.types import EveCharacterType

if 'allianceauth.eveonline.autogroups' in settings.INSTALLED_APPS:
    _has_auto_groups = True
    from allianceauth.eveonline.autogroups.models import *
else:
    _has_auto_groups = False


class Query:
    login_url = graphene.String()
    me = graphene.Field(UserType)
    user_groups = graphene.List(GroupType)
    user_characters = graphene.List(EveCharacterType, description="List of the user's alts")

    def resolve_login_url(self, info):
        oauth = OAuth2Session(
            app_settings.ESI_SSO_CLIENT_ID,
            redirect_uri=app_settings.ESI_SSO_CALLBACK_URL,
            scope=getattr(settings, 'GRAPHQL_LOGIN_SCOPES', ['publicData'])
        )

        redirect_url, state = oauth.authorization_url(app_settings.ESI_OAUTH_LOGIN_URL)

        return redirect_url

    @login_required
    def resolve_me(self, info):
        return info.context.user

    @login_required
    def resolve_user_groups(self, info):
        groups = info.context.user.groups.all()
        if _has_auto_groups:
            groups = groups\
                .filter(managedalliancegroup__isnull=True)\
                .filter(managedcorpgroup__isnull=True)
        return groups.order_by('name').annotate(status=Value(1))

    @login_required
    def resolve_user_characters(self, info):
        return EveCharacter.objects.filter(character_ownership__user=info.context.user)\
            .select_related()\
            .order_by('character_name')
