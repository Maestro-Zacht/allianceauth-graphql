import graphene
from graphql_jwt.decorators import login_required, permission_required
from graphene_django_extras import DjangoFilterPaginateListField, LimitOffsetGraphqlPagination

from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter

from allianceauth_pve.models import Rotation
from allianceauth_pve.actions import running_averages
from allianceauth_graphql.eveonline.types import EveCharacterType

from .types import RotationType, EntryType, RattingSummaryType


User = get_user_model()


class Query:
    rotation = graphene.Field(RotationType, id=graphene.Int(required=True))
    closed_rotations = graphene.List(RotationType)
    char_running_averages = graphene.Field(RattingSummaryType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    active_rotations = graphene.List(RotationType)
    rotation_entries = DjangoFilterPaginateListField(EntryType, pagination=LimitOffsetGraphqlPagination(), fields=['rotation_id'])
    search_rotation_characters = graphene.List(EveCharacterType, name=graphene.String(), exclude_characters_ids=graphene.List(graphene.Int))

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
        ratting_users = User.objects.filter(
            Q(groups__permissions__codename='access_pve') |
            Q(user_permissions__codename='access_pve') |
            Q(profile__state__permissions__codename='access_pve'),
            profile__main_character__isnull=False,
        )

        ownerships = CharacterOwnership.objects.filter(user__in=ratting_users)
        results = EveCharacter.objects.filter(pk__in=ownerships.values('character'))

        if name:
            results = results.filter(character_name__icontains=name)

        if len(exclude_characters_ids) > 0:
            results = results.exclude(pk__in=exclude_characters_ids)

        return results
