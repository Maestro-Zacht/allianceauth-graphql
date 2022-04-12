import graphene
from graphql_jwt.decorators import login_required, permission_required
from graphene_django_extras import DjangoFilterPaginateListField, LimitOffsetGraphqlPagination

from django.utils import timezone
from django.db.models import Sum, Subquery
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter

from allianceauth_pve.models import Rotation, EntryCharacter
from allianceauth_graphql.eveonline.types import EveCharacterType

from .types import RotationType, EntryType, RattingSummaryType


User = get_user_model()


class Query:
    rotation = graphene.Field(RotationType, id=graphene.Int(required=True))
    closed_rotations = graphene.List(RotationType)
    char_running_averages = graphene.Field(RattingSummaryType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    active_rotations = graphene.List(RotationType)
    rotation_entries = DjangoFilterPaginateListField(EntryType, pagination=LimitOffsetGraphqlPagination(), fields=['rotation_id'])
    search_rotation_characters = graphene.List(EveCharacterType, name=graphene.String(required=True))

    @permission_required('allianceauth_pve.view_rotation')
    @login_required
    def resolve_rotation(self, info, id):
        return Rotation.objects.get(pk=id)

    @permission_required('allianceauth_pve.view_rotation')
    @login_required
    def resolve_closed_rotations(self, info):
        return Rotation.objects.filter(is_closed=True).order_by('-closed_at')

    @login_required
    def resolve_char_running_averages(self, info, start_date, end_date=timezone.now().date()):
        user = info.context.user
        rotations = Rotation.objects.filter(closed_at__range=(start_date, end_date)).get_setup_summary().filter(user_id=user).values('total_setups')
        return EntryCharacter.objects.filter(entry__rotation__closed_at__range=(start_date, end_date), user=user)\
            .values('user').order_by()\
            .annotate(helped_setups=Coalesce(Subquery(rotations[:1]), 0))\
            .annotate(estimated_total=Sum('estimated_share_total'))\
            .annotate(actual_total=Sum('actual_share_total'))

    @permission_required('allianceauth_pve.view_rotation')
    @login_required
    def resolve_active_rotations(self, info):
        return Rotation.objects.filter(is_closed=False).order_by('-priority')

    @permission_required('allianceauth_pve.view_rotation')
    @login_required
    def resolve_search_rotation_characters(self, info, name):
        mains = CharacterOwnership.objects.filter(character__character_name__icontains=name).values('user__profile__main_character')
        return EveCharacter.objects.filter(pk__in=mains).distinct()
