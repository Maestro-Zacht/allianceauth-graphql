import datetime

import graphene
# from graphene_django.forms.mutation import DjangoFormMutation
from graphql_jwt.decorators import login_required, permission_required

from django.utils import timezone

from allianceauth.timerboard.models import Timer

from .inputs import TimerInput
from .types import StructureTimerType


class AddTimerMutation(graphene.Mutation):
    class Arguments:
        input = TimerInput(required=True)

    ok = graphene.Boolean()
    timer = graphene.Field(StructureTimerType)

    @classmethod
    @login_required
    @permission_required('auth.timer_management')
    def mutate(cls, root, info, input):
        if input.days_left < 0:
            return cls(ok=False)
        if input.hours_left < 0 or input.hours_left > 23:
            return cls(ok=False)
        if input.minutes_left < 0 or input.minutes_left > 59:
            return cls(ok=False)

        user = info.context.user
        char = user.profile.main_character

        timer = Timer()

        timer.details = input.details
        timer.system = input.system
        timer.planet_moon = input.planet_moon
        timer.structure = input.structure
        timer.timer_type = input.timer_type
        timer.objective = input.objective

        timer.eve_time = timezone.now() + datetime.timedelta(
            days=input.days_left,
            hours=input.hours_left,
            minutes=input.minutes_left
        )

        timer.important = input.important
        timer.corp_timer = input.corp_timer
        timer.user = user
        timer.eve_character = char
        timer.eve_corp = char.corporation

        timer.save()

        return cls(ok=True, timer=timer)


class EditTimerMutation(graphene.Mutation):
    class Arguments:
        input = TimerInput(required=True)
        timer_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    timer = graphene.Field(StructureTimerType)

    @classmethod
    @login_required
    @permission_required('auth.timer_management')
    def mutate(cls, root, info, input, timer_id):
        if input.days_left < 0:
            return cls(ok=False)
        if input.hours_left < 0 or input.hours_left > 23:
            return cls(ok=False)
        if input.minutes_left < 0 or input.minutes_left > 59:
            return cls(ok=False)

        user = info.context.user
        char = user.profile.main_character

        timer = Timer.objects.get(pk=timer_id)

        timer.details = input.details
        timer.system = input.system
        timer.planet_moon = input.planet_moon
        timer.structure = input.structure
        timer.timer_type = input.timer_type
        timer.objective = input.objective

        timer.eve_time = timezone.now() + datetime.timedelta(
            days=input.days_left,
            hours=input.hours_left,
            minutes=input.minutes_left
        )

        timer.important = input.important
        timer.corp_timer = input.corp_timer
        timer.user = user
        timer.eve_character = char
        timer.eve_corp = char.corporation

        timer.save()

        return cls(ok=True, timer=timer)


class DeleteTimerMutation(graphene.Mutation):
    class Arguments:
        timer_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.timer_management')
    def mutate(cls, root, info, timer_id):
        Timer.objects.filter(pk=timer_id).delete()
        return cls(ok=True)


class Mutation:
    tmr_add_timer = AddTimerMutation.Field()
    tmr_edit_timer = EditTimerMutation.Field()
    tmr_delete_timer = DeleteTimerMutation.Field()
