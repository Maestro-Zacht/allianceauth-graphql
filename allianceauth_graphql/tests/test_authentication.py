import json
import re
from urllib.parse import quote_plus
from unittest.mock import patch
from faker import Faker

from django.test import override_settings, TestCase, modify_settings
from django.core import mail, signing
from django.urls import reverse
from graphene_django.utils.testing import GraphQLTestCase

from app_utils.testdata_factories import UserMainFactory, EveCharacterFactory, UserFactory
from app_utils.testing import add_character_to_user, add_new_token, generate_invalid_pk, create_authgroup

from esi.models import Token
from esi import app_settings
from allianceauth.eveonline.autogroups.models import AutogroupsConfig

from ..authentication.types import LoginStatus


MOCK_REGISTRATION_SALT = "testing"
MOCK_REDIRECT_SITE = 'https://example.com'


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
                esiTokenAuth(ssoToken: $sso_token) {
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
        token = content['data']['esiTokenAuth']['token']

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'esiTokenAuth': {
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
                esiTokenAuth(ssoToken: $sso_token) {
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
                    'esiTokenAuth': {
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
                esiTokenAuth(ssoToken: $sso_token) {
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
                    'esiTokenAuth': {
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
                esiTokenAuth(ssoToken: $sso_token) {
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
                    'esiTokenAuth': {
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

    @patch('esi.managers.TokenManager.create_from_code')
    def test_token_equivalent_exists(self, mock_create_from_code):
        newtoken = add_new_token(self.user, self.user.profile.main_character, ["publicData"])

        mock_create_from_code.return_value = newtoken

        response = self.query(
            '''
            mutation testM($sso_token: String!) {
                esiTokenAuth(ssoToken: $sso_token) {
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
                    'esiTokenAuth': {
                        'errors': [],
                        'status': LoginStatus.LOGGED_IN.name,
                        'me': {
                            'id': str(self.user.pk)
                        }
                    }
                }
            }
        )

        self.assertFalse(
            Token.objects
            .filter(pk=newtoken.pk)
            .exists()
        )

    @patch('esi.managers.TokenManager.create_from_code')
    def test_not_able_to_authenticate(self, mock_create_from_code):
        mock_create_from_code.return_value = self.token

        self.user.is_active = False
        self.user.save()

        response = self.query(
            '''
            mutation testM($sso_token: String!) {
                esiTokenAuth(ssoToken: $sso_token) {
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
                    'esiTokenAuth': {
                        'errors': ['Unable to authenticate the selected character'],
                        'status': LoginStatus.ERROR.name,
                        'me': None
                    }
                }
            }
        )


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
                authenticationEmailRegistration(input: $input) {
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
                    'authenticationEmailRegistration': {
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
                authenticationEmailRegistration(input: $input) {
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
                    'authenticationEmailRegistration': {
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
                authenticationEmailRegistration(input: $input) {
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
                    'authenticationEmailRegistration': {
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
                authenticationChangeMainCharacter(newMainCharacterId: $input) {
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
                    'authenticationChangeMainCharacter': {
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
                authenticationChangeMainCharacter(newMainCharacterId: $input) {
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
                    'authenticationChangeMainCharacter': {
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
                authenticationChangeMainCharacter(newMainCharacterId: $input) {
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
                    'authenticationChangeMainCharacter': {
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
                authenticationAddCharacter(newCharSsoToken: $input) {
                    errors
                    ok
                    me {
                        id
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
                    'authenticationAddCharacter': {
                        'errors': [],
                        'ok': True,
                        'me': {
                            'id': str(self.user.pk),
                        }
                    }
                }
            }
        )

        self.assertEqual(self.user.character_ownerships.count(), 1)
        self.assertEqual(self.user.character_ownerships.first().character, self.newchar)


class TestRefreshEsiTokenMutation(GraphQLTestCase):

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
                esiRefreshToken(tokenId: $input) {
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
                    'esiRefreshToken': {
                        'errors': [],
                        'ok': True,
                    }
                }
            }
        )

        self.assertTrue(mock_refresh.called)

    def test_token_not_exists(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                esiRefreshToken(tokenId: $input) {
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
                    'esiRefreshToken': {
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
                esiRefreshToken(tokenId: $input) {
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
                    'esiRefreshToken': {
                        'errors': ["This token does not belong to you."],
                        'ok': False,
                    }
                }
            }
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
                esiRefreshToken(tokenId: $input) {
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
                    'esiRefreshToken': {
                        'errors': ["Failed to refresh token. Test"],
                        'ok': False,
                    }
                }
            }
        )

        self.assertTrue(mock_refresh.called)


class TestRemoveEsiTokenMutation(GraphQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()
        cls.token = cls.user.token_set.first()

    def test_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                esiRemoveToken(tokenId: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data=self.token.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'esiRemoveToken': {
                        'errors': [],
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(self.user.token_set.count(), 0)

    def test_token_not_belongs_to_user(self):
        user2 = UserFactory()

        self.client.force_login(user2, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                esiRemoveToken(tokenId: $input) {
                    errors
                    ok
                }
            }
            ''',
            operation_name='testM',
            input_data=self.token.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'esiRemoveToken': {
                        'errors': ["This token does not belong to you."],
                        'ok': False,
                    }
                }
            }
        )

        self.assertEqual(self.user.token_set.count(), 1)

    def test_token_not_exists(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation testM($input: Int!) {
                esiRemoveToken(tokenId: $input) {
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
                    'esiRemoveToken': {
                        'errors': ["Token does not exist"],
                        'ok': False,
                    }
                }
            }
        )

        self.assertEqual(self.user.token_set.count(), 1)


@override_settings(
    REGISTRATION_SALT=MOCK_REGISTRATION_SALT,
    REDIRECT_SITE=MOCK_REDIRECT_SITE
)
class TestVerifyEmailView(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_active=False)

    def test_ok(self):
        activation_key = signing.dumps([self.user.pk, self.user.email], salt=MOCK_REGISTRATION_SALT)

        email = self.user.email
        self.user.email = ''
        self.user.save()

        response = self.client.get(reverse('allianceauth_graphql:verify_email') + f"?activation_key={activation_key}")

        self.assertRedirects(
            response,
            MOCK_REDIRECT_SITE + '/registration/callback/',
            fetch_redirect_response=False
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, email)
        self.assertTrue(self.user.is_active)

    def test_not_ok(self):
        activation_key = signing.dumps([self.user.pk, self.user.email], salt=MOCK_REGISTRATION_SALT + 'WRONG')

        self.user.email = ''
        self.user.save()

        response = self.client.get(reverse('allianceauth_graphql:verify_email') + f"?activation_key={activation_key}")

        self.assertContains(response, 'Invalid signature', html=True)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, '')
        self.assertFalse(self.user.is_active)


class TestQueries(GraphQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

    def test_login_url(self):
        response = self.query(
            '''
            query q {
                esiLoginUrl(scopes: ["test1", "test2"])
            }
            '''
        )

        data = json.loads(response.content)
        self.assertIn('data', data)
        self.assertIn('esiLoginUrl', data['data'])

        login_url = data['data']['esiLoginUrl']

        self.assertRegex(login_url, rf"{re.escape(app_settings.ESI_OAUTH_LOGIN_URL)}\?response_type=code\&client_id=[0-9a-z]+\&redirect_uri={re.escape(quote_plus(app_settings.ESI_SSO_CALLBACK_URL))}\&scope={re.escape(quote_plus('test1 test2'))}\&state=[0-9a-zA-Z]+")

    def test_me(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                me {
                    id
                }
            }
            '''
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

    @modify_settings(INSTALLED_APPS={'remove': ['allianceauth.eveonline.autogroups']})
    def test_user_groups(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        group1 = create_authgroup()
        self.user.groups.add(group1)

        response = self.query(
            '''
            query q {
                authenticationUserGroups {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'authenticationUserGroups': [
                        {
                            'id': str(group1.pk)
                        }
                    ]
                }
            }
        )

    def test_user_groups_exclude_autogroups(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        group1 = create_authgroup()
        self.user.groups.add(group1)

        config: AutogroupsConfig = AutogroupsConfig.objects.create(
            corp_groups=True,
            alliance_groups=True
        )

        config.states.add(self.user.profile.state)

        response = self.query(
            '''
            query q {
                authenticationUserGroups {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'authenticationUserGroups': [
                        {
                            'id': str(group1.pk)
                        }
                    ]
                }
            }
        )

    def test_user_characters(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                authenticationUserCharacters {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'authenticationUserCharacters': [
                        {
                            'id': str(self.user.profile.main_character.pk)
                        }
                    ]
                }
            }
        )
