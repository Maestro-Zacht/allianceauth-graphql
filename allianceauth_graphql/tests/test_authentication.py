import json
from unittest.mock import patch
from faker import Faker

from django.test import override_settings
from django.core import mail
from graphene_django.utils.testing import GraphQLTestCase

from app_utils.testdata_factories import UserMainFactory, EveCharacterFactory, UserFactory
from app_utils.testing import add_character_to_user, add_new_token, generate_invalid_pk

from esi.models import Token
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
        cls.user1, cls.user2 = UserFactory.create_batch(2)

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


class TestAddCharacterMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.newchar = EveCharacterFactory()

    @patch('esi.managers.TokenManager.create_from_code')
    def test_ok(self, mock_create_from_code):
        mock_create_from_code.return_value = add_new_token(self.user, self.newchar)

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: String!) {
                addCharacter(newCharSsoToken: $input) {
                    errors
                    ok
                    me {
                        id
                        characterOwnerships {
                            character {
                                id
                            }
                        }
                    }
                }
            }
            ''',
            operation_name='testM',
            input_data='nice_token'
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'addCharacter': {
                        'errors': [],
                        'ok': True,
                        'me': {
                            'id': str(self.user.pk),
                            'characterOwnerships': [
                                {
                                    'character': {
                                        'id': str(self.newchar.pk)
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        )

    # TODO: enable with new version of app utils
    @patch('esi.managers.TokenManager.create_from_code')
    def disabled_test_not_owned(self, mock_create_from_code):
        user2 = UserFactory()
        add_character_to_user(user2, self.newchar, is_main=True)

        mock_create_from_code.return_value = add_new_token(self.user, self.newchar)

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: String!) {
                addCharacter(newCharSsoToken: $input) {
                    errors
                    ok
                    me {
                        id
                        characterOwnerships {
                            character {
                                id
                            }
                        }
                    }
                }
            }
            ''',
            operation_name='testM',
            input_data='nice_token'
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'addCharacter': {
                        'errors': ['This character already has an account'],
                        'ok': False,
                        'me': {
                            'id': str(self.user.pk),
                            'characterOwnerships': []
                        }
                    }
                }
            }
        )


class TestRemoveEsiTokenMutation(GraphQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    @patch('esi.models.Token.refresh')
    def test_ok(self, mock_refresh):
        mock_refresh.return_value = None

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        newtoken = add_new_token(
            self.user,
            EveCharacterFactory()
        )

        response = self.query(
            '''
            mutation testM($input: Int!) {
                removeEsiToken(tokenId: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data=newtoken.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'removeEsiToken': {
                        'errors': [],
                        'ok': True,
                    }
                }
            }
        )

        self.assertFalse(
            Token.objects
            .filter(pk=newtoken.pk)
            .exists()
        )

    def test_token_not_exists(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                removeEsiToken(tokenId: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data=generate_invalid_pk(Token)
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'removeEsiToken': {
                        'errors': ["Token does not exist"],
                        'ok': False,
                    }
                }
            }
        )

    def test_token_not_belongs_to_user(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        newuser = UserFactory()
        newtoken = add_new_token(
            newuser,
            EveCharacterFactory()
        )

        response = self.query(
            '''
            mutation testM($input: Int!) {
                removeEsiToken(tokenId: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data=newtoken.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'removeEsiToken': {
                        'errors': ["This token does not belong to you."],
                        'ok': False,
                    }
                }
            }
        )

        self.assertTrue(
            Token.objects
            .filter(pk=newtoken.pk)
            .exists()
        )

    @patch('esi.models.Token.refresh')
    def test_exception(self, mock_refresh):
        mock_refresh.side_effect = Exception('Test')

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        newtoken = add_new_token(
            self.user,
            EveCharacterFactory()
        )

        response = self.query(
            '''
            mutation testM($input: Int!) {
                removeEsiToken(tokenId: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data=newtoken.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'removeEsiToken': {
                        'errors': ["Failed to refresh token. Test"],
                        'ok': False,
                    }
                }
            }
        )

        self.assertTrue(
            Token.objects
            .filter(pk=newtoken.pk)
            .exists()
        )
