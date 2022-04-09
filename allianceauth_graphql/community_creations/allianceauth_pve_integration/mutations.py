import datetime
import graphene
from graphql_jwt.decorators import login_required

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Sum

from allianceauth_pve.actions import EntryService
from allianceauth_pve.models import Rotation, EntryCharacter

from .inputs import EntryInput, CreateRotationInput, RotationCloseInput
from .types import RotationType, EntryType


class CreateRattingEntry(graphene.Mutation):
    class Arguments:
        input = EntryInput(required=True)
        rotation_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    @login_required
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
    def mutate(root, info, input, entry_id):
        entry = EntryService.edit_entry(info.context.user, entry_id, input.estimated_total, input.shares)
        return ModifyRattingEntry(ok=True, rotation=entry.rotation)


class DeleteRattingEntry(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        entry_id = graphene.ID(required=True)

    @login_required
    def mutate(root, info, entry_id):
        rotation = EntryService.delete_entry(info.context.user, entry_id)
        return DeleteRattingEntry(ok=True, rotation=rotation)


class CreateRotation(graphene.Mutation):
    ok = graphene.Boolean()
    rotation = graphene.Field(RotationType)

    class Arguments:
        input = CreateRotationInput(required=True)

    @login_required
    def mutate(root, info, input):
        user = info.context.user

        if not user.is_staff:
            raise Exception('Permission Denied')

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
    def mutate(root, info, input):
        user = info.context.user
        rotation = Rotation.objects.get(pk=input.rotation_id)

        if not user.is_staff:
            raise Exception('Permission Denied')

        if rotation.is_closed:
            raise Exception('Rotation is closed and can not be modified')

        rotation.actual_total = input.sales_value
        rotation.is_closed = True
        rotation.closed_at = timezone.now()
        rotation.save()

        # update_rotation_totals(rotation_id=rotation.pk).execute()

        for entry in rotation.entries.all():
            entry.update_share_totals()

        shares = EntryCharacter.objects.filter(entry__rotation=rotation)
        User = get_user_model()
        chars = User.objects.filter(pk__in=shares.values('character'))
        rotation.summary.all().delete()

        for character in chars.all():
            shares = EntryCharacter.objects.filter(entry__rotation=rotation, character=character)

            shares_totals = shares.aggregate(estimated_total=Sum('estimated_share_total'), actual_total=Sum('actual_share_total'))

            helped_setups = 0

            start_date = rotation.created_at.date()
            end_date = rotation.closed_at.date() if rotation.is_closed else timezone.now().date()

            shares_helped_setup = shares.filter(helped_setup=True)

            for day in (start_date + datetime.timedelta(n) for n in range((end_date - start_date).days + 1)):
                for day_share in shares_helped_setup.filter(entry__created_at__date=day).all():
                    if day_share.entry.shares.count() > 2:
                        helped_setups += 1
                        break

            rotation.summary.update_or_create(
                character=character,
                defaults={
                    'estimated_total': shares_totals['estimated_total'],
                    'actual_total': shares_totals['actual_total'],
                    'helped_setup': helped_setups,
                }
            )

        return CloseRotation(ok=True)


class Mutation:
    allianceauth_pve_create_entry = CreateRattingEntry.Field()
    allianceauth_pve_modify_entry = ModifyRattingEntry.Field()
    allianceauth_pve_delete_entry = DeleteRattingEntry.Field()
    allianceauth_pve_create_rotation = CreateRotation.Field()
    allianceauth_pve_close_rotation = CloseRotation.Field()
