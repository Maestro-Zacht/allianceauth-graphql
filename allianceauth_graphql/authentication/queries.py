import graphene


class Query(graphene.ObjectType):
    test = graphene.String(default_value='test')
