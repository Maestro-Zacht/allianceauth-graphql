import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.utils import timezone

from allianceauth.optimer.models import OpTimer

from .types import OpTimerModelType


class Query:
    optimer_past_timers = graphene.List(OpTimerModelType)
    optimer_future_timers = graphene.List(OpTimerModelType)

    @login_required
    @permission_required('auth.optimer_view')
    def resolve_optimer_past_timers(self, info):
        return OpTimer.objects.filter(start__lt=timezone.now()).order_by('-start')

    @login_required
    @permission_required('auth.optimer_view')
    def resolve_optimer_future_timers(self, info):
        return OpTimer.objects.filter(start__gte=timezone.now())
