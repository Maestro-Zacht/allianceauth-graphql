from graphene_django.utils.testing import GraphQLTestCase

from app_utils.testdata_factories import UserMainFactory


class TestTypes(GraphQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

    def test_zkill_link(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                me {
                    profile {
                        mainCharacter {
                            zkillboard
                        }
                    }
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'me': {
                        'profile': {
                            'mainCharacter': {
                                'zkillboard': f"https://zkillboard.com/character/{self.user.profile.main_character.character_id}/"
                            }
                        }
                    }
                }
            }
        )
