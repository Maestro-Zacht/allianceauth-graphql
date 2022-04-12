import graphene


class EntryCharacterInput(graphene.InputObjectType):
    share_count = graphene.Int(required=True)
    user_id = graphene.Int(required=True)
    helped_setup = graphene.Boolean(default_value=False)


class EntryInput(graphene.InputObjectType):
    estimated_total = graphene.Float(required=True)
    shares = graphene.List(EntryCharacterInput, required=True)


class CreateRotationInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    tax_rate = graphene.Float(required=True)
    priority = graphene.Int(default_value=0.0)


class RotationCloseInput(graphene.InputObjectType):
    rotation_id = graphene.Int(required=True)
    sales_value = graphene.Float(required=True)


class CharactersStatsInput(graphene.InputObjectType):
    start_date = graphene.Date(required=True)
    end_date = graphene.Date(required=True)
