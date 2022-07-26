import graphene


class ApplicationResponseInputType(graphene.InputObjectType):
    question_id = graphene.Int(required=True)
    answer = graphene.List(graphene.String, required=True)


class FormAnswerInputType(graphene.InputObjectType):
    responses = graphene.List(ApplicationResponseInputType, required=True)
    form_id = graphene.ID(required=True)
