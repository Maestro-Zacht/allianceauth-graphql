import graphene
from graphql_jwt.decorators import user_passes_test, login_required

from allianceauth.corputils.views import access_corpstats_test
from allianceauth.corputils.models import CorpStats, CorpMember

from .types import CorpStatsType, CorpMemberType


class Query:
    get_corpstats = graphene.List(CorpStatsType)
    get_corpstats_corp = graphene.Field(CorpStatsType, corp_id=graphene.Int(required=True))
    search_corpstats = graphene.List(CorpMemberType, search_string=graphene.String(required=True))

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_get_corpstats(self, info):
        return CorpStats.objects.visible_to(info.context.user).order_by('corp__corporation_name').select_related('corp')

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_get_corpstats_corp(self, info, corp_id):
        avaiable = CorpStats.objects.visible_to(info.context.user)
        stats = CorpStats.objects.get(corp__corporation_id=corp_id)
        if stats in avaiable:
            return stats

    @login_required
    @user_passes_test(access_corpstats_test)
    def resolve_search_corpstats(self, info, search_string):
        # original code, inefficient
        # results = []
        # has_similar = CorpStats.objects.filter(members__character_name__icontains=search_string).visible_to(info.context.user).distinct()
        # for corpstats in has_similar:
        #     similar = corpstats.members.filter(character_name__icontains=search_string)
        #     for s in similar:
        #         results.append((corpstats, s))
        # results = sorted(results, key=lambda x: x[1].character_name)

        # my code
        avaiable = CorpStats.objects.visible_to(info.context.user)
        return CorpMember.objects\
            .filter(corpstats__in=avaiable, character_name__icontains=search_string)\
            .order_by('character_name')
