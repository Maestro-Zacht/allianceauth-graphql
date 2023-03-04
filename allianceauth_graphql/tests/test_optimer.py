import datetime
from graphene_django.utils.testing import GraphQLTestCase
from django.utils import timezone

from allianceauth.tests.test_auth_utils import AuthUtils
from app_utils.testdata_factories import UserFactory, UserMainFactory

from allianceauth.optimer.models import OpTimer, OpTimerType


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.optimer_view', UserFactory(), False)

        cls.timer_past = OpTimer.objects.create(start=timezone.now() - datetime.timedelta(days=1))
        cls.timer_future = OpTimer.objects.create(start=timezone.now() + datetime.timedelta(days=1))

    def test_optimer_past_timers(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                optimerPastTimers {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerPastTimers': [
                        {
                            'id': str(self.timer_past.pk)
                        }
                    ]
                }
            }
        )

    def test_optimer_future_timers(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                optimerFutureTimers {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerFutureTimers': [
                        {
                            'id': str(self.timer_future.pk)
                        }
                    ]
                }
            }
        )


class TestOpFormMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.optimer_management', UserMainFactory(), False)

        cls.form_data = {
            'doctrine': 'Test Doctrine',
            'system': 'Test System',
            'start': (timezone.now() + datetime.timedelta(days=1)).isoformat(),
            'duration': '1h',
            'operationName': 'Test Operation',
            'fc': 'Test FC',
        }

    def test_ok_no_type(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: OpFormMutationInput!) {
                optimerNewOp(input: $input) {
                    op {
                        doctrine
                        system
                        start
                        duration
                        operationName
                        fc
                        eveCharacter {
                            id
                        }
                    }
                }
            }
            ''',
            input_data=self.form_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerNewOp': {
                        'op': {
                            'doctrine': self.form_data['doctrine'],
                            'system': self.form_data['system'],
                            'start': self.form_data['start'],
                            'duration': self.form_data['duration'],
                            'operationName': self.form_data['operationName'],
                            'fc': self.form_data['fc'],
                            'eveCharacter': {
                                'id': str(self.user.profile.main_character.pk)
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 1)
        self.assertEqual(OpTimerType.objects.count(), 0)

    def test_ok_with_existing_type(self):
        self.client.force_login(self.user)

        optimer_tipe = OpTimerType.objects.create(type='Test Type')

        response = self.query(
            '''
            mutation($input: OpFormMutationInput!) {
                optimerNewOp(input: $input) {
                    op {
                        doctrine
                        system
                        start
                        duration
                        operationName
                        fc
                        eveCharacter {
                            id
                        }
                        type {
                            id
                        }
                    }
                }
            }
            ''',
            input_data={
                **self.form_data,
                'type': optimer_tipe.type
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerNewOp': {
                        'op': {
                            'doctrine': self.form_data['doctrine'],
                            'system': self.form_data['system'],
                            'start': self.form_data['start'],
                            'duration': self.form_data['duration'],
                            'operationName': self.form_data['operationName'],
                            'fc': self.form_data['fc'],
                            'eveCharacter': {
                                'id': str(self.user.profile.main_character.pk)
                            },
                            'type': {
                                'id': str(optimer_tipe.pk)
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 1)
        self.assertEqual(OpTimerType.objects.count(), 1)

    def test_ok_with_new_type(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: OpFormMutationInput!) {
                optimerNewOp(input: $input) {
                    op {
                        doctrine
                        system
                        start
                        duration
                        operationName
                        fc
                        eveCharacter {
                            id
                        }
                        type {
                            type
                        }
                    }
                }
            }
            ''',
            input_data={
                **self.form_data,
                'type': 'Test Type'
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerNewOp': {
                        'op': {
                            'doctrine': self.form_data['doctrine'],
                            'system': self.form_data['system'],
                            'start': self.form_data['start'],
                            'duration': self.form_data['duration'],
                            'operationName': self.form_data['operationName'],
                            'fc': self.form_data['fc'],
                            'eveCharacter': {
                                'id': str(self.user.profile.main_character.pk)
                            },
                            'type': {
                                'type': 'Test Type'
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 1)
        self.assertEqual(OpTimerType.objects.count(), 1)


class TestRemoveOpTimerMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.optimer_management', UserMainFactory(), False)

        cls.timer = OpTimer.objects.create()

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($optimerId: ID!) {
                optimerRemoveOp(optimerId: $optimerId) {
                    ok
                }
            }
            ''',
            variables={
                'optimerId': self.timer.pk
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerRemoveOp': {
                        'ok': True
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 0)


class TestOpFormEditMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.optimer_management', UserMainFactory(), False)

        cls.timer = OpTimer.objects.create()

        cls.form_data = {
            'opId': cls.timer.pk,
            'doctrine': 'Test Doctrine',
            'system': 'Test System',
            'start': (timezone.now() + datetime.timedelta(days=1)).isoformat(),
            'duration': '1h',
            'operationName': 'Test Operation',
            'fc': 'Test FC',
        }

    def test_ok_no_type(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: OpFormEditMutationInput!) {
                optimerEditOp(input: $input) {
                    op {
                        doctrine
                        system
                        start
                        duration
                        operationName
                        fc
                        eveCharacter {
                            id
                        }
                    }
                }
            }
            ''',
            input_data=self.form_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerEditOp': {
                        'op': {
                            'doctrine': self.form_data['doctrine'],
                            'system': self.form_data['system'],
                            'start': self.form_data['start'],
                            'duration': self.form_data['duration'],
                            'operationName': self.form_data['operationName'],
                            'fc': self.form_data['fc'],
                            'eveCharacter': {
                                'id': str(self.user.profile.main_character.pk)
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 1)
        self.assertEqual(OpTimerType.objects.count(), 0)

    def test_ok_with_existing_type(self):
        optimer_tipe = OpTimerType.objects.create(type='Test Type')

        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: OpFormEditMutationInput!) {
                optimerEditOp(input: $input) {
                    op {
                        doctrine
                        system
                        start
                        duration
                        operationName
                        fc
                        eveCharacter {
                            id
                        }
                        type {
                            id
                        }
                    }
                }
            }
            ''',
            input_data={
                **self.form_data,
                'type': optimer_tipe.type
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerEditOp': {
                        'op': {
                            'doctrine': self.form_data['doctrine'],
                            'system': self.form_data['system'],
                            'start': self.form_data['start'],
                            'duration': self.form_data['duration'],
                            'operationName': self.form_data['operationName'],
                            'fc': self.form_data['fc'],
                            'eveCharacter': {
                                'id': str(self.user.profile.main_character.pk)
                            },
                            'type': {
                                'id': str(optimer_tipe.pk)
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 1)
        self.assertEqual(OpTimerType.objects.count(), 1)

    def test_ok_with_new_type(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: OpFormEditMutationInput!) {
                optimerEditOp(input: $input) {
                    op {
                        doctrine
                        system
                        start
                        duration
                        operationName
                        fc
                        eveCharacter {
                            id
                        }
                        type {
                            type
                        }
                    }
                }
            }
            ''',
            input_data={
                **self.form_data,
                'type': 'Test Type'
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'optimerEditOp': {
                        'op': {
                            'doctrine': self.form_data['doctrine'],
                            'system': self.form_data['system'],
                            'start': self.form_data['start'],
                            'duration': self.form_data['duration'],
                            'operationName': self.form_data['operationName'],
                            'fc': self.form_data['fc'],
                            'eveCharacter': {
                                'id': str(self.user.profile.main_character.pk)
                            },
                            'type': {
                                'type': 'Test Type'
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(OpTimer.objects.count(), 1)
        self.assertEqual(OpTimerType.objects.count(), 1)
