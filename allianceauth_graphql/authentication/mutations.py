import graphene


class Test(graphene.Mutation):
    class Arguments:
        test = graphene.Int()

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, test=0):
        return cls(ok=True)


class Mutation(graphene.ObjectType):
    test = Test.Field()
