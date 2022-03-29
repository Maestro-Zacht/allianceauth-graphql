import graphene
import importlib
from django.conf import settings


def create_schema() -> graphene.Schema:
    mutations = []
    queries = []
    for app in settings.INSTALLED_APPS:
        if app.startswith('allianceauth.'):
            import_module = app.replace('allianceauth.', 'allianceauth_graphql.')
            if importlib.util.find_spec(import_module) is not None:
                module = importlib.import_module(import_module)
                queries.append(module.schema.Query)
                mutations.append(module.schema.Mutation)

    queries.append(graphene.ObjectType)
    mutations.append(graphene.ObjectType)

    Query = type('Query', queries, {})
    Mutation = type('Mutation', mutations, {})

    return graphene.Schema(query=Query, mutation=Mutation)


schema = create_schema()
