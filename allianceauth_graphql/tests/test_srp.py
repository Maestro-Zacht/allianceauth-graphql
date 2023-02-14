import datetime
from graphene_django.utils.testing import GraphQLTestCase
from unittest.mock import patch

from django.utils import timezone
from django.db.models import Min

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testdata_factories import UserFactory, UserMainFactory
from app_utils.esi_testing import EsiEndpoint, EsiClientStub
from app_utils.testing import generate_invalid_pk

from allianceauth.srp.models import SrpFleetMain, SrpUserRequest
from allianceauth.eveonline.models import EveCharacter
from allianceauth.notifications.models import Notification


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('srp.access_srp', UserFactory(), False)

        cls.open_fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

        cls.completed_fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet 2',
            fleet_doctrine='Test Doctrine 2',
            fleet_time=timezone.now() - datetime.timedelta(hours=2),
            fleet_srp_code='TEST2',
            fleet_srp_status='Completed',
        )

    def test_srp_get_fleets_all(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($all: Boolean) {
                srpGetFleets(all: $all) {
                    id
                }
            }
            ''',
            variables={'all': True}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpGetFleets': [
                        {
                            'id': str(self.open_fleet.pk),
                        },
                        {
                            'id': str(self.completed_fleet.pk),
                        },
                    ]
                }
            }
        )

    def test_srp_get_fleets_not_all(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($all: Boolean) {
                srpGetFleets(all: $all) {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpGetFleets': [
                        {
                            'id': str(self.open_fleet.pk),
                        },
                    ]
                }
            }
        )


class TestAddFleetMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

        cls.input_data = {
            'fleetName': 'Test Fleet',
            'fleetDoctrine': 'Test Doctrine',
            'fleetTime': (timezone.now() - datetime.timedelta(hours=1)).isoformat(),
        }

    def test_decorator_no_perms(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: AddFleetMutationInput!) {
                srpAddFleet(input: $input) {
                    ok
                }
            }
            ''',
            input_data=self.input_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpAddFleet': None
                },
                'errors': [
                    {
                        'message': 'You do not have permission to perform this action',
                        'locations': [
                            {
                                'line': 3,
                                'column': 17
                            }
                        ],
                        'path': [
                            'srpAddFleet'
                        ]
                    }
                ]
            }
        )

    def test_ok(self):
        user = AuthUtils.add_permission_to_user_by_name('srp.add_srpfleetmain', self.user, False)

        self.client.force_login(user)

        response = self.query(
            '''
            mutation($input: AddFleetMutationInput!) {
                srpAddFleet(input: $input) {
                    ok
                    srpFleet {
                        fleetName
                        fleetDoctrine
                        fleetCommander {
                            id
                        }
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
                    'srpAddFleet': {
                        'ok': True,
                        'srpFleet': {
                            'fleetName': self.input_data['fleetName'],
                            'fleetDoctrine': self.input_data['fleetDoctrine'],
                            'fleetCommander': {
                                'id': str(user.profile.main_character.pk),
                            },
                        }
                    }
                }
            }
        )

        self.assertEqual(SrpFleetMain.objects.count(), 1)


class TestRemoveDisableEnableCompletedUncompletedFleetMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.srp_management', UserFactory(), False)

        cls.fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

    def test_remove_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fleetId: ID!) {
                srpRemoveFleet(fleetId: $fleetId) {
                    ok
                }
            }
            ''',
            variables={'fleetId': self.fleet.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpRemoveFleet': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(SrpFleetMain.objects.count(), 0)

    def test_disable_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fleetId: ID!) {
                srpDisableFleet(fleetId: $fleetId) {
                    ok
                    srpFleet {
                        id
                        fleetSrpCode
                    }
                }
            }
            ''',
            variables={'fleetId': self.fleet.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpDisableFleet': {
                        'ok': True,
                        'srpFleet': {
                            'id': str(self.fleet.pk),
                            'fleetSrpCode': '',
                        }
                    }
                }
            }
        )

    @patch('allianceauth_graphql.srp.mutations.random_string')
    def test_enable_ok(self, mock_random_string):
        self.client.force_login(self.user)

        mock_random_string.return_value = 'TESTTEST'

        self.fleet.fleet_srp_code = ''
        self.fleet.save()

        response = self.query(
            '''
            mutation($fleetId: ID!) {
                srpEnableFleet(fleetId: $fleetId) {
                    ok
                    srpFleet {
                        id
                        fleetSrpCode
                    }
                }
            }
            ''',
            variables={'fleetId': self.fleet.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpEnableFleet': {
                        'ok': True,
                        'srpFleet': {
                            'id': str(self.fleet.pk),
                            'fleetSrpCode': 'TESTTEST',
                        }
                    }
                }
            }
        )

    def test_completed_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fleetId: ID!) {
                srpMarkCompleted(fleetId: $fleetId) {
                    ok
                    srpFleet {
                        id
                        fleetSrpStatus
                    }
                }
            }
            ''',
            variables={'fleetId': self.fleet.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpMarkCompleted': {
                        'ok': True,
                        'srpFleet': {
                            'id': str(self.fleet.pk),
                            'fleetSrpStatus': 'Completed',
                        }
                    }
                }
            }
        )

    def test_uncompleted_ok(self):
        self.client.force_login(self.user)

        self.fleet.fleet_srp_status = 'Completed'
        self.fleet.save()

        response = self.query(
            '''
            mutation($fleetId: ID!) {
                srpMarkUncompleted(fleetId: $fleetId) {
                    ok
                    srpFleet {
                        id
                        fleetSrpStatus
                    }
                }
            }
            ''',
            variables={'fleetId': self.fleet.pk}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpMarkUncompleted': {
                        'ok': True,
                        'srpFleet': {
                            'id': str(self.fleet.pk),
                            'fleetSrpStatus': '',
                        }
                    }
                }
            }
        )


class TestSrpFleetUserRequestFormMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('srp.access_srp', UserMainFactory(), False)

        cls.fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

        cls.form_data = {
            'fleetSrpCode': 'TEST',
            'killboardLink': 'https://zkillboard.com/kill/1234567890/',
        }

    @patch('allianceauth.srp.managers.SRPManager.get_kill_data')
    @patch('allianceauth_graphql.srp.mutations.esi')
    def test_ok(self, mock_esi, mock_get_kill_data):
        self.client.force_login(self.user)

        endpoints = [
            EsiEndpoint(
                'Universe',
                'get_universe_types_type_id',
                'type_id',
                data={
                    '11567': {
                        'name': 'Avatar'
                    }
                }
            ),
        ]

        mock_esi.client = EsiClientStub.create_from_endpoints(endpoints)
        mock_get_kill_data.return_value = (11567, 64_840_457_150.95, self.user.profile.main_character.character_id)

        response = self.query(
            '''
            mutation($input: SrpFleetUserRequestFormMutationInput!) {
                srpRequest(input: $input) {
                    ok
                    srpRequest {
                        killboardLink
                        srpFleetMain {
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
                    'srpRequest': {
                        'ok': True,
                        'srpRequest': {
                            'killboardLink': self.form_data['killboardLink'],
                            'srpFleetMain': {
                                'id': str(self.fleet.pk),
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.count(), 1)

    @patch('allianceauth.srp.managers.SRPManager.get_kill_data')
    def test_value_error(self, mock_get_kill_data):
        self.client.force_login(self.user)

        mock_get_kill_data.side_effect = ValueError('Test')

        response = self.query(
            '''
            mutation($input: SrpFleetUserRequestFormMutationInput!) {
                srpRequest(input: $input) {
                    ok
                    srpRequest {
                        killboardLink
                        srpFleetMain {
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
                    'srpRequest': {
                        'ok': False,
                        'srpRequest': None
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.count(), 0)

    @patch('allianceauth.srp.managers.SRPManager.get_kill_data')
    def test_missing_character(self, mock_get_kill_data):
        self.client.force_login(self.user)

        mock_get_kill_data.return_value = (
            11567,
            64_840_457_150.95,
            EveCharacter.objects
            .aggregate(Min('character_id'))['character_id__min'] - 1
        )

        response = self.query(
            '''
            mutation($input: SrpFleetUserRequestFormMutationInput!) {
                srpRequest(input: $input) {
                    ok
                    srpRequest {
                        killboardLink
                        srpFleetMain {
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
                    'srpRequest': {
                        'ok': False,
                        'srpRequest': None
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.count(), 0)

    def test_already_requested(self):
        self.client.force_login(self.user)

        SrpUserRequest.objects.create(
            srp_fleet_main=self.fleet,
            character=self.user.profile.main_character,
            killboard_link=self.form_data['killboardLink'],
            srp_ship_name='Avatar',
        )

        response = self.query(
            '''
            mutation($input: SrpFleetUserRequestFormMutationInput!) {
                srpRequest(input: $input) {
                    ok
                    srpRequest {
                        killboardLink
                        srpFleetMain {
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
                    'srpRequest': {
                        'ok': False,
                        'srpRequest': None
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.count(), 1)


class TestSrpRequestRemoveMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.srp_management', UserMainFactory(), False)

        cls.fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

        cls.request = SrpUserRequest.objects.create(
            srp_fleet_main=cls.fleet,
            character=cls.user.profile.main_character,
            killboard_link='https://zkillboard.com/kill/1234567890/',
            srp_ship_name='Avatar',
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($requestIds: [ID!]!) {
                srpRemoveRequests(requestIds: $requestIds) {
                    ok
                }
            }
            ''',
            variables={'requestIds': [self.request.pk]}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpRemoveRequests': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.count(), 0)


class TestSrpRequestApproveRejectMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.srp_management', UserMainFactory(), False)

        fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

        cls.request = SrpUserRequest.objects.create(
            srp_fleet_main=fleet,
            character=cls.user.profile.main_character,
            killboard_link='https://zkillboard.com/kill/1234567890/',
            srp_ship_name='Avatar',
            srp_total_amount=64_840_457_150.95,
        )

        cls.request2 = SrpUserRequest.objects.create(
            srp_fleet_main=fleet,
            character=cls.user.profile.main_character,
            killboard_link='https://zkillboard.com/kill/12345067890/',
            srp_ship_name='Avatar',
            kb_total_loss=64_840_457_150.95,
        )

    def test_approve_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($requestIds: [ID!]!) {
                srpApproveRequests(requestIds: $requestIds) {
                    ok
                }
            }
            ''',
            variables={
                'requestIds': [
                    self.request.pk,
                    self.request2.pk,
                    generate_invalid_pk(SrpUserRequest)
                ]
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpApproveRequests': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.filter(srp_status='Approved').count(), 2)
        self.assertEqual(Notification.objects.count(), 2)

    def test_reject_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($requestIds: [ID!]!) {
                srpRejectRequests(requestIds: $requestIds) {
                    ok
                }
            }
            ''',
            variables={
                'requestIds': [
                    self.request.pk,
                    self.request2.pk,
                    generate_invalid_pk(SrpUserRequest)
                ]
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpRejectRequests': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(SrpUserRequest.objects.filter(srp_status='Rejected').count(), 2)
        self.assertEqual(Notification.objects.count(), 2)


class TestSrpUpdateAmountMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.srp_management', UserMainFactory(), False)

        fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

        cls.request = SrpUserRequest.objects.create(
            srp_fleet_main=fleet,
            character=cls.user.profile.main_character,
            killboard_link='https://zkillboard.com/kill/1234567890/',
            srp_ship_name='Avatar',
            srp_total_amount=64_840_457_150.95,
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fleetSrpRequestId: ID!, $srpTotalAmount: Float!) {
                srpUpdateAmount(fleetSrpRequestId: $fleetSrpRequestId, srpTotalAmount: $srpTotalAmount) {
                    ok
                }
            }
            ''',
            variables={
                'fleetSrpRequestId': self.request.pk,
                'srpTotalAmount': 1234.56
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpUpdateAmount': {
                        'ok': True,
                    }
                }
            }
        )

        self.request.refresh_from_db()

        self.assertEqual(self.request.srp_total_amount, 1234)

    def test_missing_request(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fleetSrpRequestId: ID!, $srpTotalAmount: Float!) {
                srpUpdateAmount(fleetSrpRequestId: $fleetSrpRequestId, srpTotalAmount: $srpTotalAmount) {
                    ok
                }
            }
            ''',
            variables={
                'fleetSrpRequestId': generate_invalid_pk(SrpUserRequest),
                'srpTotalAmount': 1234.56
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpUpdateAmount': {
                        'ok': False,
                    }
                }
            }
        )

        self.request.refresh_from_db()

        self.assertEqual(self.request.srp_total_amount, 64_840_457_150)


class TestSrpUpdateAARMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.srp_management', UserFactory(), False)

        cls.fleet = SrpFleetMain.objects.create(
            fleet_name='Test Fleet',
            fleet_doctrine='Test Doctrine',
            fleet_time=timezone.now() - datetime.timedelta(hours=1),
            fleet_srp_code='TEST',
            fleet_srp_status='',
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fleetId: ID!, $fleetSrpAarLink: String!) {
                srpUpdateAar(fleetId: $fleetId, fleetSrpAarLink: $fleetSrpAarLink) {
                    ok
                }
            }
            ''',
            variables={
                'fleetId': self.fleet.pk,
                'fleetSrpAarLink': 'Test AAR'
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'srpUpdateAar': {
                        'ok': True,
                    }
                }
            }
        )

        self.fleet.refresh_from_db()

        self.assertEqual(self.fleet.fleet_srp_aar_link, 'Test AAR')
