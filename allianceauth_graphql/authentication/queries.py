import graphene
from graphql_jwt.decorators import login_required
from esi import app_settings
from requests_oauthlib import OAuth2Session
from django.conf import settings


class Query(graphene.ObjectType):
    login_url = graphene.String()

    def resolve_login_url(self, info):
        oauth = OAuth2Session(
            app_settings.ESI_SSO_CLIENT_ID,
            redirect_uri=app_settings.ESI_SSO_CALLBACK_URL,
            scope=getattr(settings, 'GRAPHQL_LOGIN_SCOPES', ['publicData'])
        )

        redirect_url, state = oauth.authorization_url(app_settings.ESI_OAUTH_LOGIN_URL)

        return redirect_url
