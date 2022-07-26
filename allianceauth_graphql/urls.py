from django.urls import path
from django.conf import settings
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from .schema import schema
from .authentication.views import verify_email

app_name = 'allianceauth_graphql'


urlpatterns = [
    path("", csrf_exempt(GraphQLView.as_view(graphiql=getattr(settings, 'SHOW_GRAPHIQL', True), schema=schema)), name='graphql'),
    path('verify/', verify_email, name='verify_email')
]
