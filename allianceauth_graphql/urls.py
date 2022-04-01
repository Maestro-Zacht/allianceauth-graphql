from django.urls import path
from django.conf import settings
from graphene_django.views import GraphQLView
from django.shortcuts import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .schema import schema

app_name = 'allianceauth_graphql'


def test_view(request):
    return HttpResponse('Test!')


urlpatterns = [
    path("", csrf_exempt(GraphQLView.as_view(graphiql=getattr(settings, 'SHOW_GRAPHIQL', True), schema=schema)), name='graphql'),
    path('test', test_view, name='test'),
]
