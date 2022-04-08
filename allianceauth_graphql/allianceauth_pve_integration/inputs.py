import graphene


class EntryCharacterInput(graphene.InputObjectType):
    share_count = graphene.Int(required=True)
    character_id = graphene.Int(required=True)
    helped_setup = graphene.Boolean(required=True)


class EntryInput(graphene.InputObjectType):
    estimated_total = graphene.Float(required=True)
    shares = graphene.List(EntryCharacterInput, required=True)
    helpedSetup = graphene.Boolean()


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
