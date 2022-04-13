import datetime
import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Sum

from allianceauth_pve.actions import EntryService
from allianceauth_pve.models import Rotation

from .inputs import EntryInput, CreateRotationInput, RotationCloseInput
from .types import RotationType, EntryType


class CreateRattingEntry(graphene.Mutation):
    class Arguments:
        input = EntryInput(required=True)
        rotation_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    @login_required
    @permission_required('allianceauth_pve.add_entry')
    def mutate(root, info, input, rotation_id):
        entry = EntryService.create_entry(info.context.user, rotation_id, input.estimated_total, input.shares)
        return CreateRattingEntry(ok=True, rotation=entry.rotation)


class ModifyRattingEntry(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        input = EntryInput(required=True)
        entry_id = graphene.ID(required=True)

    @login_required
    @permission_required('allianceauth_pve.change_entry')
    def mutate(root, info, input, entry_id):
        entry = EntryService.edit_entry(info.context.user, entry_id, input.estimated_total, input.shares)
        return ModifyRattingEntry(ok=True, rotation=entry.rotation)


class DeleteRattingEntry(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        entry_id = graphene.ID(required=True)

    @login_required
    @permission_required('allianceauth_pve.delete_entry')
    def mutate(root, info, entry_id):
        rotation = EntryService.delete_entry(info.context.user, entry_id)
        return DeleteRattingEntry(ok=True, rotation=rotation)


class CreateRotation(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        input = CreateRotationInput(required=True)

    @login_required
    @permission_required('allianceauth_pve.add_rotation')
    def mutate(root, info, input):
        rotation = Rotation.objects.create(
            name=input.name,
            tax_rate=input.tax_rate,
            priority=input.priority if input.priority else 0,
        )

        return CreateRotation(ok=True, rotation=rotation)


class CloseRotation(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        input = RotationCloseInput(required=True)

    @login_required
    @permission_required('allianceauth_pve.close_rotation')
    def mutate(root, info, input):
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

        return CloseRotation(ok=True)


class Mutation:
    allianceauth_pve_create_entry = CreateRattingEntry.Field()
    allianceauth_pve_modify_entry = ModifyRattingEntry.Field()
    allianceauth_pve_delete_entry = DeleteRattingEntry.Field()
    allianceauth_pve_create_rotation = CreateRotation.Field()
    allianceauth_pve_close_rotation = CloseRotation.Field()
