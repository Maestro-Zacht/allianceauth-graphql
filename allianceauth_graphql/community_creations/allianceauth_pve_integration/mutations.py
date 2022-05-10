import datetime
import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.db import transaction

from allianceauth.services.hooks import get_extension_logger
from allianceauth.authentication.models import CharacterOwnership

from allianceauth_pve.models import Rotation, Entry, EntryRole, EntryCharacter

from .inputs import EntryInput, CreateRotationInput, RotationCloseInput
from .types import RotationType, EntryType

logger = get_extension_logger(__name__)


class CreateRattingEntry(graphene.Mutation):
    class Arguments:
        input = EntryInput(required=True)
        rotation_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    entry = graphene.Field(EntryType)
    errors = graphene.List(graphene.String)

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_entries')
    def mutate(cls, root, info, input, rotation_id):
        ok = True
        errors = []

        # input checks

        roles = set()
        for new_role in input.roles:
            if new_role['name'] in roles:
                ok = False
                errors.append(f"{new_role['name']} name is not unique")
            else:
                roles.add(new_role['name'])

        characters_ids = set()
        for new_share in input.shares:
            if new_share['character_id'] in characters_ids:
                ok = False
                errors.append(f"character {new_share['character_id']} cannot have more than 1 share")
            else:
                characters_ids.add(new_share['character_id'])

            if new_share['role'] not in roles:
                ok = False
                errors.append(f"{new_share['role']} is not a valid role")

            if not CharacterOwnership.objects.filter(user_id=new_share['user_id'], character_id=new_share['character_id']).exists():
                ok = False
                errors.append("character ownership doesn't match")

        if ok:
            with transaction.atomic():
                entry = Entry.objects.create(
                    rotation_id=rotation_id,
                    estimated_total=input['estimated_total'],
                    created_by=info.context.user
                )

                to_add = []

                for new_role in input.roles:
                    to_add.append(EntryRole(
                        entry=entry,
                        name=new_role['name'],
                        value=new_role['value']
                    ))

                EntryRole.objects.bulk_create(to_add)
                to_add.clear()

                setups = set()

                for new_share in input.shares:
                    role = entry.roles.get(name=new_share['role'])

                    setup = new_share['helped_setup'] and new_share['user_id'] not in setups
                    if setup:
                        setups.add(new_share['user_id'])

                    to_add.append(EntryCharacter(
                        entry=entry,
                        role=role,
                        user_character_id=new_share['character_id'],
                        user_id=new_share['user_id'],
                        site_count=new_share['site_count'],
                        helped_setup=setup,
                    ))

                EntryCharacter.objects.bulk_create(to_add)

                entry.update_share_totals()
        else:
            entry = None

        return cls(ok=ok, errors=errors, entry=entry)


class ModifyRattingEntry(graphene.Mutation):
    ok = graphene.Boolean()
    entry = graphene.Field(EntryType)
    errors = graphene.List(graphene.String)

    class Arguments:
        input = EntryInput(required=True)
        entry_id = graphene.Int(required=True)

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_entries')
    def mutate(cls, root, info, input, entry_id):
        ok = True
        errors = []
        user = info.context.user
        entry = Entry.objects.get(pk=entry_id)

        # input checks

        roles = set()
        for new_role in input.roles:
            if new_role['name'] in roles:
                ok = False
                errors.append(f"{new_role['name']} name is not unique")
            else:
                roles.add(new_role['name'])

        characters_ids = set()
        for new_share in input.shares:
            if new_share['character_id'] in characters_ids:
                ok = False
                errors.append(f"character {new_share['character_id']} cannot have more than 1 share")
            else:
                characters_ids.add(new_share['character_id'])

            if new_share['role'] not in roles:
                ok = False
                errors.append(f"{new_share['role']} is not a valid role")

            if not CharacterOwnership.objects.filter(user_id=new_share['user_id'], character_id=new_share['character_id']).exists():
                ok = False
                errors.append("character ownership doesn't match")

        if user != entry.created_by and not user.is_superuser:
            ok = False
            errors.append('You cannot edit this entry')

        if ok:
            with transaction.atomic():
                entry.ratting_shares.all().delete()
                entry.roles.all().delete()
                entry.estimated_total = input['estimated_total']
                entry.save()

                to_add = []

                for new_role in input.roles:
                    to_add.append(EntryRole(
                        entry=entry,
                        name=new_role['name'],
                        value=new_role['value']
                    ))

                EntryRole.objects.bulk_create(to_add)
                to_add.clear()

                setups = set()

                for new_share in input.shares:
                    role = entry.roles.get(name=new_share['role'])

                    setup = new_share['helped_setup'] and new_share['user_id'] not in setups
                    if setup:
                        setups.add(new_share['user_id'])

                    to_add.append(EntryCharacter(
                        entry=entry,
                        role=role,
                        user_character_id=new_share['character_id'],
                        user_id=new_share['user_id'],
                        site_count=new_share['site_count'],
                        helped_setup=setup,
                    ))

                EntryCharacter.objects.bulk_create(to_add)

                entry.update_share_totals()

        return cls(ok=ok, errors=errors, entry=entry)


class DeleteRattingEntry(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        entry_id = graphene.Int(required=True)

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_entries')
    def mutate(cls, root, info, entry_id):
        user = info.context.user
        entry = Entry.objects.select_related('rotation').get(pk=entry_id)
        rotation = entry.rotation
        return cls(ok=True, rotation=rotation)


class CreateRotation(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        input = CreateRotationInput(required=True)

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_rotations')
    def mutate(cls, root, info, input):
        rotation = Rotation.objects.create(
            name=input.name,
            tax_rate=input.tax_rate,
            priority=input.priority if input.priority else 0,
        )

        return cls(ok=True, rotation=rotation)


class CloseRotation(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        input = RotationCloseInput(required=True)

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_rotations')
    def mutate(cls, root, info, input):
        user = info.context.user
        rotation = Rotation.objects.get(pk=input.rotation_id)

        if rotation.is_closed:
            raise Exception('Rotation is closed and can not be modified')

        rotation.actual_total = input.sales_value
        rotation.is_closed = True
        rotation.closed_at = timezone.now()
        rotation.save()

        for entry in rotation.entries.all():
            entry.update_share_totals()

        return cls(ok=True)


class Mutation:
    allianceauth_pve_create_entry = CreateRattingEntry.Field()
    allianceauth_pve_modify_entry = ModifyRattingEntry.Field()
    allianceauth_pve_delete_entry = DeleteRattingEntry.Field()
    allianceauth_pve_create_rotation = CreateRotation.Field()
    allianceauth_pve_close_rotation = CloseRotation.Field()
