import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.db.models import Q
from django.utils import timezone

from allianceauth.timerboard.models import Timer

from .types import StructureTimerType


class Query:
    tmr_future_timers = graphene.List(StructureTimerType, required=True)
    tmr_past_timers = graphene.List(StructureTimerType, required=True)

    @login_required
    @permission_required('auth.timer_view')
    def resolve_tmr_future_timers(self, info):
        return Timer.objects.filter(
            (
                Q(corp_timer=True) &
                Q(eve_corp=info.context.user.profile.main_character.corporation)
            ) |
            Q(corp_timer=False),
            eve_time__gte=timezone.now()
        )

    @login_required
    @permission_required('auth.timer_view')
    def resolve_tmr_past_timers(self, info):
        return Timer.objects.filter(
            (
                Q(corp_timer=True) &
                Q(eve_corp=info.context.user.profile.main_character.corporation)
            ) |
            Q(corp_timer=False),
            eve_time__lt=timezone.now()
        )
