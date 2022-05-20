import datetime

import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import ExtractMonth, ExtractYear
from django.db.models import Count

from allianceauth.fleetactivitytracking.models import Fatlink, Fat
from allianceauth.fleetactivitytracking.views import MemberStat, first_day_of_next_month, CorpStat
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCorporationInfo, EveCharacter

from .types import FatlinkType, FatType, FatUserStatsType, FatCorpStatsType, FatPersonalStatsType, FatPersonalMonthlyStatsType


User = get_user_model()


class Query:
    recent_fat = graphene.List(FatType, num=graphene.Int())
    fatlinks = graphene.List(FatlinkType, num=graphene.Int())
    fat_corp_monthly_stats = graphene.List(FatUserStatsType, corp_id=graphene.Int(required=True), year=graphene.Int(required=True), month=graphene.Int(required=True))
    fat_general_monthly_stats = graphene.List(FatCorpStatsType, year=graphene.Int(required=True), month=graphene.Int(required=True))
    fat_personal_stats = graphene.List(FatPersonalStatsType)
    fat_personal_monthly_stats = graphene.Field(FatPersonalMonthlyStatsType, year=graphene.Int(required=True), month=graphene.Int(required=True), char_id=graphene.Int())

    @login_required
    def resolve_recent_fat(self, info, num=5):
        return Fat.objects.filter(user=info.context.user).order_by('-id')[:num]

    @login_required
    @permission_required('auth.fleetactivitytracking')
    def resolve_fatlinks(self, info, num=5):
        return Fatlink.objects.order_by('-id')[:num]

    @login_required
    @permission_required('auth.fleetactivitytracking_statistics')
    def resolve_fat_corp_monthly_stats(self, info, corp_id, year, month):
        start_of_month = datetime.datetime(year, month, 1)
        start_of_next_month = first_day_of_next_month(year, month)

        corp_members = CharacterOwnership.objects.filter(character__corporation_id=corp_id).order_by('user_id').values('user_id').distinct()

        fat_stats = {}

        for member in corp_members:
            try:
                fat_stats[member['user_id']] = MemberStat(User.objects.get(pk=member['user_id']), start_of_month, start_of_next_month)
            except ObjectDoesNotExist:
                continue

        stat_list = [{
            'user': x.mainchar.character_ownership.user,
            'num_chars': x.n_chars,
            'num_fats': x.n_fats,
            'average_fats': x.avg_fat
        } for x in fat_stats]
        stat_list.sort(key=lambda stat: stat['user'].profile.main_character.character_name)
        stat_list.sort(key=lambda stat: (stat['num_fats'], stat['avg_fat']), reverse=True)

        return stat_list

    @login_required
    @permission_required('auth.fleetactivitytracking_statistics')
    def resolve_fat_general_monthly_stats(self, info, year, month):
        start_of_month = datetime.datetime(year, month, 1)
        start_of_next_month = first_day_of_next_month(year, month)

        fat_stats = {}

        for corp in EveCorporationInfo.objects.all():
            fat_stats[corp.corporation_id] = CorpStat(corp.corporation_id, start_of_month, start_of_next_month)

        # get FAT stats for corps without models
        fats_in_span = Fat.objects.filter(fatlink__fatdatetime__gte=start_of_month).filter(
            fatlink__fatdatetime__lt=start_of_next_month).exclude(character__corporation_id__in=fat_stats)

        for fat in fats_in_span.exclude(character__corporation_id__in=fat_stats):
            if EveCorporationInfo.objects.filter(corporation_id=fat.character.corporation_id).exists():
                fat_stats[fat.character.corporation_id] = CorpStat(fat.character.corporation_id, start_of_month, start_of_next_month)

        # collect and sort stats
        stat_list = [{
            'corporation': x.corp,
            'num_fats': x.n_fats,
            'avg_fats': x.avg_fat,
        } for x in fat_stats]
        stat_list.sort(key=lambda stat: stat['corporation'].corporation_name)
        stat_list.sort(key=lambda stat: (stat['num_fats'], stat['avg_fat']), reverse=True)

        return stat_list

    @login_required
    def resolve_fat_personal_stats(self, info):
        # my optimized code
        return Fat.objects.filter(user=info.context.user)\
            .annotate(month=ExtractMonth('fatlink__fatdatetime'))\
            .annotate(year=ExtractYear('fatlink__fatdatetime'))\
            .values('month', 'year')\
            .annotate(num_fats=Count('*'))\
            .order_by('-year', '-month')

    @login_required
    def resolve_fat_personal_monthly_stats(self, info, year, month, char_id=None):
        if char_id and info.context.user.has_perm('auth.fleetactivitytracking_statistics'):
            user = EveCharacter.objects.get(character_id=char_id).character_ownership.user
        else:
            user = info.context.user

        # my optimized code
        personal_fats = Fat.objects.filter(user=user, fatlink__fatdatetime__year=year, fatlink__fatdatetime__month=month)\
            .values('shiptype')\
            .annotate(times_used=Count('*'))\
            .order_by('shiptype')

        created_fats = Fatlink.objects.filter(creator=user, fatdatetime__year=year, fatdatetime__month=month)

        return {
            'collected_links': personal_fats,
            'created_links': created_fats,
        }
