import graphene
from graphql_jwt.decorators import login_required

from graphene_django_extras import DjangoFilterPaginateListField, LimitOffsetGraphqlPagination

from allianceauth_pve.models import Rotation

from .types import RotationType, EntryType


class Query:
    rotation = graphene.Field(RotationType, id=graphene.Int(required=True))
    rotations = graphene.List(RotationType)
    # running_averages = graphene.List(CharacterStatsType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    # char_running_averages = graphene.Field(CharacterStatsType, start_date=graphene.Date(required=True), end_date=graphene.Date())
    active_rotations = graphene.List(RotationType)
    rotation_entries = DjangoFilterPaginateListField(EntryType, pagination=LimitOffsetGraphqlPagination(), fields=['rotation_id'])

    @login_required
    def resolve_rotation(self, info, id):
        return Rotation.objects.get(pk=id)

    @login_required
    def resolve_rotations(self, info):
        return Rotation.objects.filter(is_closed=True).order_by('-closed_at')

    # @login_required
    # def resolve_running_averages(self, info, start_date, end_date=now().date()):
    #     results = [
    #         {
    #             'character': char,
    #             **RattingService.character_stats_task(char.character_id, start_date.isoformat(), end_date.isoformat())
    #         } for char in CharacterService.get_all_instances()
    #     ]

    #     return sorted(results, key=lambda k: k['total_earned'], reverse=True)

    # @login_required
    # def resolve_char_running_averages(self, info, start_date, end_date=now().date()):
    #     char = info.context.user
    #     return {'character': char, **RattingService.character_stats_task(char.character_id, start_date.isoformat(), end_date.isoformat())}

    @login_required
    def resolve_active_rotations(self, info):
        return Rotation.objects.filter(is_closed=False).order_by('-priority')
