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
        # elif app == 'allianceauth_pve':
        #     import_module = 'allianceauth_pve_integration'
        else:
            import_module = None

        if import_module is not None:
            try:
                print(import_module)
                module = importlib.import_module(import_module)
            except ModuleNotFoundError:
                print('fail')
            else:
                print("success")
                queries.append(module.Query)
                mutations.append(module.Mutation)

    from . import allianceauth_pve_integration

    class Query(*queries, allianceauth_pve_integration.Query, graphene.ObjectType):
        pass

    class Mutation(*mutations, allianceauth_pve_integration.Mutation, graphene.ObjectType):
        pass

    return graphene.Schema(query=Query, mutation=Mutation)


schema = create_schema()
