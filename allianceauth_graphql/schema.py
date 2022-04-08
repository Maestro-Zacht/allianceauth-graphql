import graphene
import importlib
from django.conf import settings

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
            import_module = f'community_creations.{app}_integration'
        else:
            import_module = None

        if import_module is not None:
            try:
                module = importlib.import_module(import_module)
            except ModuleNotFoundError:
                pass
            else:
                queries.append(module.Query)
                mutations.append(module.Mutation)

    class Query(*queries, graphene.ObjectType):
        pass

    class Mutation(*mutations, graphene.ObjectType):
        pass

    return graphene.Schema(query=Query, mutation=Mutation)


schema = create_schema()
