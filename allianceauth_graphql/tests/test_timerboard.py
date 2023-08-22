import datetime
from graphene_django.utils.testing import GraphQLTestCase

from django.utils import timezone

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testdata_factories import UserMainFactory, EveCorporationInfoFactory

from allianceauth.timerboard.models import Timer, TimerType

from ..timerboard.types import TimerStructureChoices, TimerTypeChoices, TimerObjectiveChoices


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.timer_view', UserMainFactory(), False)

        cls.corp = cls.user.profile.main_character.corporation
        cls.corp2 = EveCorporationInfoFactory()

        cls.corp_future_timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() + datetime.timedelta(days=1),
            eve_corp=cls.corp,
            corp_timer=True,
        )

        cls.corp_past_timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() - datetime.timedelta(days=1),
            eve_corp=cls.corp,
            corp_timer=True,
        )

        cls.corp2_future_timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() + datetime.timedelta(days=1),
            eve_corp=cls.corp2,
            corp_timer=True,
        )

        cls.corp2_past_timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() - datetime.timedelta(days=1),
            eve_corp=cls.corp2,
            corp_timer=True,
        )

        cls.future_timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() + datetime.timedelta(days=1),
            eve_corp=cls.corp,
            corp_timer=False,
        )

        cls.past_timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() - datetime.timedelta(days=1),
            eve_corp=cls.corp,
            corp_timer=False,
        )

    def test_tmr_future_timers(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                tmrFutureTimers {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrFutureTimers': [
                        {
                            'id': str(self.corp_future_timer.pk),
                        },
                        {
                            'id': str(self.future_timer.pk),
                        },
                    ]
                }
            }
        )

    def test_tmr_past_timers(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                tmrPastTimers {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrPastTimers': [
                        {
                            'id': str(self.corp_past_timer.pk),
                        },
                        {
                            'id': str(self.past_timer.pk),
                        },
                    ]
                }
            }
        )


class TestMutations(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.timer_management', UserMainFactory(), False)

        cls.timer = Timer.objects.create(
            timer_type=TimerType.UNSPECIFIED,
            eve_time=timezone.now() + datetime.timedelta(days=1),
            eve_corp=cls.user.profile.main_character.corporation,
            corp_timer=True,
        )

        cls.input_data = {
            'details': 'test',
            'system': 'Jita',
            'structure': TimerStructureChoices.Keepstar.name,
            'timerType': TimerTypeChoices.FINAL.name,
            'objective': TimerObjectiveChoices.Neutral.name,
            'daysLeft': 2,
            'hoursLeft': 0,
            'minutesLeft': 0,
            'important': True,
            'corpTimer': False,
        }

    def test_absolute_time_ok(self):
        time = timezone.now() + datetime.timedelta(days=7)
        input_data = self.input_data.copy()
        input_data.update({'absoluteTime': time.isoformat()})
        input_data.pop('daysLeft')
        input_data.pop('hoursLeft')
        input_data.pop('minutesLeft')

        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: TimerInput!) {
                tmrAddTimer(input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                        eveTime
                    }
                }
            }
            ''',
            input_data=input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrAddTimer': {
                        'ok': True,
                        'timer': {
                            'details': 'test',
                            'system': 'Jita',
                            'structure': TimerStructureChoices.Keepstar.name,
                            'timerType': TimerTypeChoices.FINAL.name,
                            'objective': TimerObjectiveChoices.Neutral.name,
                            'important': True,
                            'corpTimer': False,
                            'eveTime': time.isoformat(),
                        }
                    }
                }
            }
        )

        self.assertEqual(Timer.objects.count(), 2)

    def test_absolute_time_error(self):
        self.input_data.pop('daysLeft')
        self.input_data.pop('hoursLeft')
        self.input_data.pop('minutesLeft')

        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: TimerInput!) {
                tmrAddTimer(input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                        eveTime
                    }
                }
            }
            ''',
            input_data=self.input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrAddTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

        self.assertEqual(Timer.objects.count(), 1)

    def test_add_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: TimerInput!) {
                tmrAddTimer(input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrAddTimer': {
                        'ok': True,
                        'timer': {
                            'details': 'test',
                            'system': 'Jita',
                            'structure': TimerStructureChoices.Keepstar.name,
                            'timerType': TimerTypeChoices.FINAL.name,
                            'objective': TimerObjectiveChoices.Neutral.name,
                            'important': True,
                            'corpTimer': False,
                        }
                    }
                }
            }
        )

    def test_add_error_days(self):
        self.client.force_login(self.user)

        self.input_data['daysLeft'] = -1

        response = self.query(
            '''
            mutation($input: TimerInput!) {
                tmrAddTimer(input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrAddTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

        self.assertEqual(Timer.objects.count(), 1)

    def test_add_error_hours(self):
        self.client.force_login(self.user)

        self.input_data['hoursLeft'] = -1

        response = self.query(
            '''
            mutation($input: TimerInput!) {
                tmrAddTimer(input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrAddTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

        self.assertEqual(Timer.objects.count(), 1)

    def test_add_error_minutes(self):
        self.client.force_login(self.user)

        self.input_data['minutesLeft'] = -1

        response = self.query(
            '''
            mutation($input: TimerInput!) {
                tmrAddTimer(input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrAddTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

        self.assertEqual(Timer.objects.count(), 1)

    def test_edit_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($timerId: ID!, $input: TimerInput!) {
                tmrEditTimer(timerId: $timerId, input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data,
            variables={'timerId': self.timer.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrEditTimer': {
                        'ok': True,
                        'timer': {
                            'details': 'test',
                            'system': 'Jita',
                            'structure': TimerStructureChoices.Keepstar.name,
                            'timerType': TimerTypeChoices.FINAL.name,
                            'objective': TimerObjectiveChoices.Neutral.name,
                            'important': True,
                            'corpTimer': False,
                        }
                    }
                }
            }
        )

    def test_edit_error_days(self):
        self.client.force_login(self.user)

        self.input_data['daysLeft'] = -1

        response = self.query(
            '''
            mutation($timerId: ID!, $input: TimerInput!) {
                tmrEditTimer(timerId: $timerId, input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data,
            variables={'timerId': self.timer.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrEditTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

    def test_edit_error_hours(self):
        self.client.force_login(self.user)

        self.input_data['hoursLeft'] = -1

        response = self.query(
            '''
            mutation($timerId: ID!, $input: TimerInput!) {
                tmrEditTimer(timerId: $timerId, input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data,
            variables={'timerId': self.timer.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrEditTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

    def test_edit_error_minutes(self):
        self.client.force_login(self.user)

        self.input_data['minutesLeft'] = -1

        response = self.query(
            '''
            mutation($timerId: ID!, $input: TimerInput!) {
                tmrEditTimer(timerId: $timerId, input: $input) {
                    ok
                    timer {
                        details
                        system
                        structure
                        timerType
                        objective
                        important
                        corpTimer
                    }
                }
            }
            ''',
            input_data=self.input_data,
            variables={'timerId': self.timer.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrEditTimer': {
                        'ok': False,
                        'timer': None,
                    }
                }
            }
        )

    def test_delete(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($timerId: ID!) {
                tmrDeleteTimer(timerId: $timerId) {
                    ok
                }
            }
            ''',
            variables={'timerId': self.timer.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tmrDeleteTimer': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(Timer.objects.count(), 0)
