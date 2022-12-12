import json
from unittest.mock import patch
from graphene_django.utils.testing import GraphQLTestCase

from esi.tests import _generate_token, _store_as_Token
from app_utils.testdata_factories import UserMainFactory

from ..authentication.types import LoginStatus


class TestEsiTokenAuthMutation(GraphQLTestCase):

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

        self.assertResponseNoErrors(response)

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
