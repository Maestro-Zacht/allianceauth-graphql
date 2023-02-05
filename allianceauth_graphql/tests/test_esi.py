from graphene_django.utils.testing import GraphQLTestCase

from app_utils.testdata_factories import UserMainFactory


class TestAll(GraphQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

    def test_user_tokens(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                esiUserTokens {
                    id
                    character {
                        id
                    }
                }
            }
            '''
        )

        self.assertEqual(self.user.token_set.count(), 1)

        token = self.user.token_set.first()

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'esiUserTokens': [
                        {
                            'id': str(token.pk),
                            'character': {
                                'id': str(self.user.profile.main_character.pk)
                            }
                        }
                    ]
                }
            }
        )
