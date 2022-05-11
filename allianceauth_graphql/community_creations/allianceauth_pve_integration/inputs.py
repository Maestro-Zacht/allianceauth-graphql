import graphene

from allianceauth.authentication.models import CharacterOwnership


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

    @staticmethod
    def is_valid(input):
        errors = []

        roles = set()
        for new_role in input.roles:
            if new_role['name'] in roles:
                errors.append(f"{new_role['name']} name is not unique")
            else:
                roles.add(new_role['name'])

        characters_ids = set()
        for new_share in input.shares:
            if new_share['character_id'] in characters_ids:
                errors.append(f"character {new_share['character_id']} cannot have more than 1 share")
            else:
                characters_ids.add(new_share['character_id'])

            if new_share['role'] not in roles:
                errors.append(f"{new_share['role']} is not a valid role")

            if not CharacterOwnership.objects.filter(user_id=new_share['user_id'], character_id=new_share['character_id']).exists():
                errors.append("character ownership doesn't match")

        return errors


class RotationCloseInput(graphene.InputObjectType):
    rotation_id = graphene.Int(required=True)
    sales_value = graphene.Float(required=True)


class CharactersStatsInput(graphene.InputObjectType):
    start_date = graphene.Date(required=True)
    end_date = graphene.Date(required=True)
