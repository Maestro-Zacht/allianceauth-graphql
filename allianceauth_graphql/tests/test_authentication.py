from django.test import override_settings
from unittest.mock import patch
from graphene_django.utils.testing import GraphQLTestCase

from app_utils.testdata_factories import UserMainFactory

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
