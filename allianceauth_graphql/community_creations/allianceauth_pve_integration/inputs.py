import graphene


class EntryRoleInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    value = graphene.Int(required=True)


class EntryCharacterInput(graphene.InputObjectType):
    site_count = graphene.Int(required=True)
    user_id = graphene.Int(required=True)
    character_id = graphene.Int(required=True)
    helped_setup = graphene.Boolean(default_value=False)
    role = graphene.String(required=True)


class EntryInput(graphene.InputObjectType):
    estimated_total = graphene.Float(required=True)
    shares = graphene.List(EntryCharacterInput, required=True)
    roles = graphene.List(EntryRoleInput, required=True)


class CreateRotationInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    tax_rate = graphene.Float(default_value=0.0)
    priority = graphene.Int(default_value=0)


class RotationCloseInput(graphene.InputObjectType):
    rotation_id = graphene.Int(required=True)
    sales_value = graphene.Float(required=True)


class CharactersStatsInput(graphene.InputObjectType):
    start_date = graphene.Date(required=True)
    end_date = graphene.Date(required=True)
