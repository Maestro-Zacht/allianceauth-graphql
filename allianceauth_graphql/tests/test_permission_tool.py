import json
from graphene_django.utils.testing import GraphQLTestCase

from django.contrib.contenttypes.models import ContentType

from app_utils.testdata_factories import UserFactory
from allianceauth.tests.test_auth_utils import AuthUtils


class TestQueries(GraphQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.perms = [
            ('permissions_tool', 'audit_permissions'),
            ('analytics', 'add_analyticsidentifier'),
            ('analytics', 'change_analyticsidentifier'),
            ('analytics', 'delete_analyticsidentifier'),
            ('analytics', 'view_analyticsidentifier'),
        ]

        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [f'{perm[0]}.{perm[1]}' for perm in cls.perms],
            cls.user,
            False
        )

    def test_show_only_applied_true(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q(
                $app_label: String
                $model: String
                $search_string: String
                $show_only_applied: Boolean
            ) {
                permsSearch(
                    appLabel: $app_label
                    model: $model
                    searchString: $search_string
                    showOnlyApplied: $show_only_applied
                ) {
                    codename
                    contentType {
                        appLabel
                    }
                }
            }
            ''',
            variables={'show_only_applied': True}
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertNotIn('errors', data)
        self.assertIn('permsSearch', data['data'])

        results = data['data']['permsSearch']

        self.assertCountEqual([(r['contentType']['appLabel'], r['codename']) for r in results], self.perms)

    def test_app_label_not_only_applied(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q(
                $app_label: String
                $model: String
                $search_string: String
                $show_only_applied: Boolean
            ) {
                permsSearch(
                    appLabel: $app_label
                    model: $model
                    searchString: $search_string
                    showOnlyApplied: $show_only_applied
                ) {
                    codename
                    contentType {
                        appLabel
                    }
                }
            }
            ''',
            variables={
                'show_only_applied': False,
                'app_label': "permissions_tool",
            }
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertNotIn('errors', data)
        self.assertIn('permsSearch', data['data'])

        results = data['data']['permsSearch']

        perms = [
            ('permissions_tool', 'add_permissionstool'),
            ('permissions_tool', 'change_permissionstool'),
            ('permissions_tool', 'delete_permissionstool'),
            ('permissions_tool', 'view_permissionstool'),
            ('permissions_tool', 'audit_permissions'),
        ]

        self.assertCountEqual([(r['contentType']['appLabel'], r['codename']) for r in results], perms)

    def test_model(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q(
                $app_label: String
                $model: String
                $search_string: String
                $show_only_applied: Boolean
            ) {
                permsSearch(
                    appLabel: $app_label
                    model: $model
                    searchString: $search_string
                    showOnlyApplied: $show_only_applied
                ) {
                    codename
                    contentType {
                        appLabel
                    }
                }
            }
            ''',
            variables={
                'show_only_applied': False,
                'model': "characterownership",
            }
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertNotIn('errors', data)
        self.assertIn('permsSearch', data['data'])

        results = data['data']['permsSearch']

        perms = [
            ('authentication', 'change_characterownership'),
            ('authentication', 'delete_characterownership'),
        ]

        self.assertCountEqual([(r['contentType']['appLabel'], r['codename']) for r in results], perms)

    def test_search_string(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q(
                $app_label: String
                $model: String
                $search_string: String
                $show_only_applied: Boolean
            ) {
                permsSearch(
                    appLabel: $app_label
                    model: $model
                    searchString: $search_string
                    showOnlyApplied: $show_only_applied
                ) {
                    codename
                    contentType {
                        appLabel
                    }
                }
            }
            ''',
            variables={
                'show_only_applied': True,
                'search_string': "audit",
            }
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertNotIn('errors', data)
        self.assertIn('permsSearch', data['data'])

        results = data['data']['permsSearch']

        perms = [
            ('permissions_tool', 'audit_permissions'),
        ]

        self.assertCountEqual([(r['contentType']['appLabel'], r['codename']) for r in results], perms)

    def test_perms_list_app_models(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q{
                permsListAppModels {
                    appLabel
                    model
                }
            }
            '''
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertNotIn('errors', data)
        self.assertIn('permsListAppModels', data['data'])

        results = data['data']['permsListAppModels']

        self.assertEqual(len(results), ContentType.objects.count())
