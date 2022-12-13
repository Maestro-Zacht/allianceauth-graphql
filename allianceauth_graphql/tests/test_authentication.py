import json
from unittest.mock import patch
from faker import Faker

from django.test import override_settings
from django.core import mail
from graphene_django.utils.testing import GraphQLTestCase

from app_utils.testdata_factories import UserMainFactory, EveCharacterFactory, UserFactory
from app_utils.testing import add_character_to_user

from ..authentication.types import LoginStatus


@override_settings(REGISTRATION_VERIFY_EMAIL=True)
class TestEsiTokenAuthMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()
        cls.token = cls.user.token_set.first()

    @patch('esi.managers.TokenManager.create_from_code')
    def test_logged_in(self, mock_create_from_code):
        mock_create_from_code.return_value = self.token

        response = self.query(
            '''
            mutation testM($sso_token: String!) {
                tokenAuth(ssoToken: $sso_token) {
                    me {
                        id
                    }
                    errors
                    status
                    token
                }
            }
            ''',
            operation_name='testM',
            variables={'sso_token': 'nice_token'}
        )

        content = json.loads(response.content)
        token = content['data']['tokenAuth']['token']

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tokenAuth': {
                        'errors': [],
                        'status': LoginStatus.LOGGED_IN.name,
                        'me': {
                            'id': str(self.user.pk)
                        },
                        'token': token
                    }
                }
            }
        )

        response = self.query(
            '''
            query q {
                me {
                    id
                }
            }
            ''',
            operation_name='q',
            headers={'HTTP_AUTHORIZATION': f'JWT {token}'}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'me': {
                        'id': str(self.user.pk)
                    }
                }
            }
        )

    @patch('allianceauth_graphql.authentication.mutations.authenticate')
    @patch('esi.managers.TokenManager.create_from_code')
    def test_user_none(self, mock_create_from_code, mock_authenticate):
        mock_create_from_code.return_value = self.token
        mock_authenticate.return_value = None

        response = self.query(
            '''
            mutation testM($sso_token: String!) {
                tokenAuth(ssoToken: $sso_token) {
                    me {
                        id
                    }
                    errors
                    status
                }
            }
            ''',
            operation_name='testM',
            variables={'sso_token': 'nice_token'}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tokenAuth': {
                        'errors': [
                            'Unable to authenticate the selected character',
                        ],
                        'status': LoginStatus.ERROR.name,
                        'me': None
                    }
                }
            }
        )

    @patch('esi.managers.TokenManager.create_from_code')
    def test_email_registration(self, mock_create_from_code):
        mock_create_from_code.return_value = self.token

        self.user.email = ''
        self.user.is_active = False
        self.user.save()

        response = self.query(
            '''
            mutation testM($sso_token: String!) {
                tokenAuth(ssoToken: $sso_token) {
                    me {
                        id
                    }
                    errors
                    status
                    token
                    refreshToken
                }
            }
            ''',
            operation_name='testM',
            variables={'sso_token': 'nice_token'}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tokenAuth': {
                        'errors': [],
                        'status': LoginStatus.REGISTRATION.name,
                        'me': None,
                        'refreshToken': None,
                        'token': None
                    }
                }
            }
        )

        self.assertIn('registration_uid', self.client.session)
        self.assertEqual(self.client.session['registration_uid'], self.user.pk)

    @override_settings(REGISTRATION_VERIFY_EMAIL=False)
    @patch('esi.managers.TokenManager.create_from_code')
    def test_email_disabled_registration(self, mock_create_from_code):
        mock_create_from_code.return_value = self.token

        self.user.email = ''
        self.user.is_active = False
        self.user.save()

        response = self.query(
            '''
            mutation testM($sso_token: String!) {
                tokenAuth(ssoToken: $sso_token) {
                    me {
                        id
                    }
                    errors
                    status
                }
            }
            ''',
            operation_name='testM',
            variables={'sso_token': 'nice_token'}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'tokenAuth': {
                        'errors': [],
                        'status': LoginStatus.LOGGED_IN.name,
                        'me': {
                            'id': str(self.user.pk)
                        }
                    }
                }
            }
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)


class TestRegistrationMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory(
            is_active=False,
            email='',
        )

    @override_settings(REDIRECT_SITE='https://www.example.com')
    def test_email_registration(self):
        session = self.client.session
        session.update({'registration_uid': self.user.pk})
        session.save()

        fake = Faker()

        response = self.query(
            '''
            mutation testM($input: RegistrationMutationInput!) {
                emailRegistration(input: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data={'email': fake.email()}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'emailRegistration': {
                        'errors': [],
                        'ok': True
                    }
                }
            }
        )

        self.assertEqual(len(mail.outbox), 1)

    @override_settings(REDIRECT_SITE='https://www.example.com')
    def test_missing_user_id(self):
        fake = Faker()

        response = self.query(
            '''
            mutation testM($input: RegistrationMutationInput!) {
                emailRegistration(input: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data={'email': fake.email()}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'emailRegistration': {
                        'errors': ['You need to do the token registration step first!'],
                        'ok': False
                    }
                }
            }
        )

        self.assertEqual(len(mail.outbox), 0)

    def test_missing_site(self):
        session = self.client.session
        session.update({'registration_uid': self.user.pk})
        session.save()

        fake = Faker()

        response = self.query(
            '''
            mutation testM($input: RegistrationMutationInput!) {
                emailRegistration(input: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data={'email': fake.email()}
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'emailRegistration': {
                        'errors': ['Redirect site not specified in settings!'],
                        'ok': False
                    }
                }
            }
        )

        self.assertEqual(len(mail.outbox), 0)


class TestChangeMainCharacterMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()

        cls.newchar = EveCharacterFactory()

    def test_ok(self):
        add_character_to_user(self.user1, self.newchar)

        self.client.force_login(self.user1, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                changeMainCharacter(newMainCharacterId: $input) {
                    errors
                    ok
                    me {
                        id
                        profile {
                            mainCharacter {
                                id
                            }
                        }
                    }
                }
            }
            ''',
            operation_name='testM',
            input_data=self.newchar.character_id
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'changeMainCharacter': {
                        'errors': [],
                        'ok': True,
                        'me': {
                            'id': str(self.user1.pk),
                            'profile': {
                                'mainCharacter': {
                                    'id': str(self.newchar.pk)
                                }
                            }
                        }
                    }
                }
            }
        )

    def test_character_not_added(self):
        self.client.force_login(self.user1, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                changeMainCharacter(newMainCharacterId: $input) {
                    errors
                    ok
                    me {
                        id
                        profile {
                            mainCharacter {
                                id
                            }
                        }
                    }
                }
            }
            ''',
            operation_name='testM',
            input_data=self.newchar.character_id
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'changeMainCharacter': {
                        'errors': ["You never added this character"],
                        'ok': False,
                        'me': {
                            'id': str(self.user1.pk),
                            'profile': {
                                'mainCharacter': None
                            }
                        }
                    }
                }
            }
        )

    def test_character_not_owned(self):
        add_character_to_user(self.user2, self.newchar)

        self.client.force_login(self.user1, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                changeMainCharacter(newMainCharacterId: $input) {
                    errors
                    ok
                    me {
                        id
                        profile {
                            mainCharacter {
                                id
                            }
                        }
                    }
                }
            }
            ''',
            operation_name='testM',
            input_data=self.newchar.character_id
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'changeMainCharacter': {
                        'errors': ["You don't own this character"],
                        'ok': False,
                        'me': {
                            'id': str(self.user1.pk),
                            'profile': {
                                'mainCharacter': None
                            }
                        }
                    }
                }
            }
        )
