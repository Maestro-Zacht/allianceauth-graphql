import graphene
from graphql_jwt.decorators import user_passes_test, login_required

from allianceauth.corputils.views import access_corpstats_test
from allianceauth.corputils.models import CorpStats, CorpMember

from .types import CorpStatsType, CorpMemberType


class Query:
    corputils_get_all_corpstats = graphene.List(CorpStatsType)
    corputils_get_corpstats_corp = graphene.Field(CorpStatsType, corp_id=graphene.Int(required=True))
    corputils_search_corpstats = graphene.List(CorpMemberType, search_string=graphene.String(required=True))

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_corputils_get_all_corpstats(self, info):
        return CorpStats.objects.visible_to(info.context.user).order_by('corp__corporation_name')

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_corputils_get_corpstats_corp(self, info, corp_id):
        avaiable = CorpStats.objects.visible_to(info.context.user)
        stats = CorpStats.objects.get(corp__corporation_id=corp_id)
        if avaiable.filter(pk=stats.pk).exists():
            return stats

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_corputils_search_corpstats(self, info, search_string):
        avaiable = CorpStats.objects.visible_to(info.context.user)
        return (
            CorpMember.objects
            .filter(
                corpstats__in=avaiable,
                character_name__icontains=search_string
            )
            .order_by('character_name')
        )
