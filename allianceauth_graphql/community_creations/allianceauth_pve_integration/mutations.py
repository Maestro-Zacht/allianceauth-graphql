import graphene
from graphene_django.forms.mutation import DjangoModelFormMutation
from graphql_jwt.decorators import login_required, permission_required

from django.utils import timezone
from django.db import transaction

from allianceauth.services.hooks import get_extension_logger

from allianceauth_pve.models import Rotation, Entry, EntryRole, EntryCharacter
from allianceauth_pve.forms import NewRotationForm

from .inputs import EntryInput, RotationCloseInput
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
        try:
            rotation = Rotation.objects.get(pk=rotation_id)
        except Rotation.DoesNotExist:
            ok = False
            errors = ["Rotation doesn't exists"]
        else:
            ok = not rotation.is_closed
            errors = [] if ok else ['The rotation is closed, you cannot add an entry']

        errors += EntryInput.is_valid(input)
        ok = ok and len(errors) == 0

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
        errors = EntryInput.is_valid(input)
        ok = len(errors) == 0
        user = info.context.user
        entry = Entry.objects.get(pk=entry_id)

        if entry.rotation.is_closed or (user != entry.created_by and not user.is_superuser):
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

        if rotation.is_closed or (user != entry.created_by and not user.is_superuser):
            ok = False
        else:
            ok = True
            entry.delete()

        return cls(ok=ok, rotation=rotation)


class CreateRotation(DjangoModelFormMutation):
    rotation = graphene.Field(RotationType)

    class Meta:
        form_class = NewRotationForm

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_rotations')
    def perform_mutate(cls, form, info):
        return super().perform_mutate(form, info)


class CloseRotation(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        input = RotationCloseInput(required=True)

    @classmethod
    @login_required
    @permission_required('allianceauth_pve.manage_rotations')
    def mutate(cls, root, info, input):
        rotation = Rotation.objects.get(pk=input.rotation_id)

        if rotation.is_closed:
            ok = False
        else:
            with transaction.atomic():
                rotation.actual_total = input.sales_value
                rotation.is_closed = True
                rotation.closed_at = timezone.now()
                rotation.save()

            ok = True

        return cls(ok=ok)


class Mutation:
    allianceauth_pve_create_entry = CreateRattingEntry.Field()
    allianceauth_pve_modify_entry = ModifyRattingEntry.Field()
    allianceauth_pve_delete_entry = DeleteRattingEntry.Field()
    allianceauth_pve_create_rotation = CreateRotation.Field()
    allianceauth_pve_close_rotation = CloseRotation.Field()
