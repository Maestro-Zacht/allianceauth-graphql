import graphene
from graphql_jwt.decorators import user_passes_test, login_required

from allianceauth.corputils.views import access_corpstats_test
from allianceauth.corputils.models import CorpStats

from .types import CorpStatsType


class Query:
    get_corpstats = graphene.List(CorpStatsType)
    get_corpstats_corp = graphene.Field(CorpStatsType, corp_id=graphene.Int(required=True))

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_get_corpstats(self, info):
        return CorpStats.objects.visible_to(info.context.user).order_by('corp__corporation_name').select_related('corp')

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_get_corpstats_corp(self, info, corp_id):
        avaiable = CorpStats.objects.visible_to(info.context.user).order_by('corp__corporation_name').select_related('corp')
        stats = CorpStats.objects.get(corp__corporation_id=corp_id)
        if stats in avaiable:
            return stats
