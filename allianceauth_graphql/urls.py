from django.urls import path
from django.conf import settings
from graphene_django.views import GraphQLView

urlpatterns = [
    path("graphql", GraphQLView.as_view(graphiql=settings.get('SHOW_GRAPHIQL', False))),
]
