import graphene
from graphql_jwt.decorators import login_required, permission_required
from graphene_django_extras import DjangoFilterPaginateListField, LimitOffsetGraphqlPagination

from django.utils import timezone
from django.db.models import OuterRef, Sum, Subquery
from django.db.models.functions import Coalesce

from allianceauth_pve.models import Rotation, EntryCharacter

from .types import RotationType, EntryType, RattingSummaryType


class Query:
    rotation = graphene.Field(RotationType, id=graphene.Int(required=True))
    closed_rotations = graphene.List(RotationType)
    char_running_averages = graphene.Field(RattingSummaryType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    active_rotations = graphene.List(RotationType)
    rotation_entries = DjangoFilterPaginateListField(EntryType, pagination=LimitOffsetGraphqlPagination(), fields=['rotation_id'])

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
        char = info.context.user
        rotations = Rotation.objects.filter(closed_at__range=(start_date, end_date)).get_setup_summary().filter(character_id=char).values('total_setups')
        return EntryCharacter.objects.filter(entry__rotation__closed_at__range=(start_date, end_date), character=char)\
            .values('character').order_by()\
            .annotate(helped_setups=Coalesce(Subquery(rotations[:1]), 0))\
            .annotate(estimated_total=Sum('estimated_share_total'))\
            .annotate(actual_total=Sum('actual_share_total'))

    @permission_required('allianceauth_pve.view_rotation')
    @login_required
    def resolve_active_rotations(self, info):
        return Rotation.objects.filter(is_closed=False).order_by('-priority')
