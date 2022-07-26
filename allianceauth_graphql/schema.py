import graphene
import importlib
from django.conf import settings

from allianceauth.services.hooks import get_extension_logger

from allianceauth_graphql.esi import Query as esi_query, Mutation as esi_mutation

logger = get_extension_logger(__name__)

community_creations = [
    'allianceauth_pve',
]


def create_schema() -> graphene.Schema:
    mutations = []
    queries = []
    for app in settings.INSTALLED_APPS:
        if app.startswith('allianceauth.'):
            import_module = app.replace('allianceauth.', 'allianceauth_graphql.')
        elif app in community_creations:
            import_module = f'allianceauth_graphql.community_creations.{app}_integration'
        else:
            import_module = None

        if import_module is not None:
            try:
                module = importlib.import_module(import_module)
            except ModuleNotFoundError:
                logger.debug(f"Loading of {app}: fail")
            else:
                logger.debug(f"Loading of {app}: success")
                queries.append(module.Query)
                mutations.append(module.Mutation)

    class Query(*queries, esi_query, graphene.ObjectType):
        pass

    class Mutation(*mutations, esi_mutation, graphene.ObjectType):
        pass

    return graphene.Schema(query=Query, mutation=Mutation)


schema = create_schema()
