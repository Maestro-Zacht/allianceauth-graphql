import graphene
from graphql_jwt.decorators import login_required, permission_required
from graphene_django_extras import DjangoFilterPaginateListField, LimitOffsetGraphqlPagination

from django.utils import timezone
from django.db.models import Sum, Subquery, Q
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model

from allianceauth.authentication.models import CharacterOwnership

from allianceauth_pve.models import Rotation, EntryCharacter
from allianceauth_graphql.authentication.types import UserType

from .types import RotationType, EntryType, RattingSummaryType


User = get_user_model()


class Query:
    rotation = graphene.Field(RotationType, id=graphene.Int(required=True))
    closed_rotations = graphene.List(RotationType)
    char_running_averages = graphene.Field(RattingSummaryType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    active_rotations = graphene.List(RotationType)
    rotation_entries = DjangoFilterPaginateListField(EntryType, pagination=LimitOffsetGraphqlPagination(), fields=['rotation_id'])
    search_rotation_characters = graphene.List(UserType, name=graphene.String(required=True))

    @login_required
    @permission_required('allianceauth_pve.view_rotation')
    def resolve_rotation(self, info, id):
        return Rotation.objects.get(pk=id)

    @login_required
    @permission_required('allianceauth_pve.view_rotation')
    def resolve_closed_rotations(self, info):
        return Rotation.objects.filter(is_closed=True).order_by('-closed_at')

    @login_required
    def resolve_char_running_averages(self, info, start_date, end_date=timezone.now()):
        user = info.context.user
        rotations = Rotation.objects.filter(closed_at__range=(start_date, end_date)).get_setup_summary().filter(user=user).values('total_setups')
        return EntryCharacter.objects.filter(entry__rotation__closed_at__range=(start_date, end_date), user=user)\
            .values('user').order_by()\
            .annotate(helped_setups=Coalesce(Subquery(rotations[:1]), 0))\
            .annotate(estimated_total=Sum('estimated_share_total'))\
            .annotate(actual_total=Sum('actual_share_total'))[0]

    @login_required
    @permission_required('allianceauth_pve.view_rotation')
    def resolve_active_rotations(self, info):
        return Rotation.objects.filter(is_closed=False).order_by('-priority')

    @login_required
    @permission_required('allianceauth_pve.view_rotation')
    def resolve_search_rotation_characters(self, info, name):
        users_ids = CharacterOwnership.objects.filter(character__character_name__icontains=name).values('user')
        return User.objects.filter(
            Q(groups__permissions__codename='view_rotation') |
            Q(user_permissions__codename='view_rotation') |
            Q(profile__state__permissions__codename='view_rotation'),
            pk__in=users_ids
        )
