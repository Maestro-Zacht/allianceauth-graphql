import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.utils import timezone
from django.db.models import Q, Exists, F, OuterRef
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter


from allianceauth_pve.models import Rotation, PveButton, RoleSetup, General
from allianceauth_pve.actions import running_averages
from allianceauth_graphql.eveonline.types import EveCharacterType

from .types import RotationType, RoleSetupType, RattingSummaryType, PveButtonType


User = get_user_model()


class Query:
    rotation = graphene.Field(RotationType, id=graphene.Int(required=True))
    closed_rotations = graphene.List(RotationType)
    char_running_averages = graphene.Field(RattingSummaryType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    active_rotations = graphene.List(RotationType)
    search_rotation_characters = graphene.List(EveCharacterType, name=graphene.String(), exclude_characters_ids=graphene.List(graphene.Int))
    roles_setups = graphene.List(RoleSetupType)
    pve_buttons = graphene.List(PveButtonType)

    @login_required
    @permission_required('allianceauth_pve.access_pve')
    def resolve_rotation(self, info, id):
        return Rotation.objects.get(pk=id)

    @login_required
    @permission_required('allianceauth_pve.access_pve')
    def resolve_closed_rotations(self, info):
        return Rotation.objects.filter(is_closed=True).order_by('-closed_at')

    @login_required
    def resolve_char_running_averages(self, info, start_date, end_date=timezone.now()):
        return running_averages(info.context.user, start_date, end_date)

    @login_required
    @permission_required('allianceauth_pve.access_pve')
    def resolve_active_rotations(self, info):
        return Rotation.objects.filter(is_closed=False).order_by('-priority')

    @login_required
    @permission_required('allianceauth_pve.manage_entries')
    def resolve_search_rotation_characters(self, info, name=None, exclude_characters_ids=[]):
        content_type = ContentType.objects.get_for_model(General)
        permission = Permission.objects.get(content_type=content_type, codename='access_pve')

        ownerships = CharacterOwnership.objects.filter(
            Q(user__groups__permissions=permission) |
            Q(user__user_permissions=permission) |
            Q(user__profile__state__permissions=permission),
            user__profile__main_character__isnull=False,
        )

        if name:
            alts_name = CharacterOwnership.objects.filter(user=OuterRef('user'), character__character_name__icontains=name)
            ownerships = ownerships.filter(
                Q(character__character_name__icontains=name) |
                (Exists(alts_name) & Q(character=F('user__profile__main_character')))
            )

        if getattr(settings, 'PVE_ONLY_MAINS', False):
            ownerships = ownerships.filter(character=F('user__profile__main_character'))

        results = EveCharacter.objects.filter(pk__in=ownerships.values('character'))

        if len(exclude_characters_ids) > 0:
            results = results.exclude(pk__in=exclude_characters_ids)

        return results

    @login_required
    @permission_required('allianceauth_pve.manage_rotations')
    def resolve_roles_setups(self, info):
        return RoleSetup.objects.all()

    @login_required
    @permission_required('allianceauth_pve.manage_rotations')
    def resolve_pve_buttons(self, info):
        return PveButton.objects.all()
