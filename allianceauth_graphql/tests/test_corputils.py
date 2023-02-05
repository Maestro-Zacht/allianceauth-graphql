import json
from graphene_django.utils.testing import GraphQLTestCase
from unittest.mock import patch

from django.db.models import Max

from allianceauth.tests.test_auth_utils import AuthUtils
from app_utils.testdata_factories import UserMainFactory, EveCharacterFactory
from app_utils.esi_testing import EsiClientStub, EsiEndpoint

from allianceauth.corputils.models import CorpStats, CorpMember


class TestQueriesAndTypes(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user, cls.user2 = UserMainFactory.create_batch(2)

        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'corputils.add_corpstats',
                'corputils.view_corp_corpstats',
            ],
            cls.user,
            False
        )

        cls.mainchar = cls.user.profile.main_character
        cls.corp = cls.mainchar.corporation

        cls.newchars = EveCharacterFactory.create_batch(9, corporation=cls.corp)

        cls.corpstat = CorpStats.objects.create(
            token=cls.user.token_set.first(),
            corp=cls.corp
        )

        cls.corpstat2 = CorpStats.objects.create(
            token=cls.user2.token_set.first(),
            corp=cls.user2.profile.main_character.corporation
        )

        CorpMember.objects.bulk_create(
            [
                CorpMember(
                    character_id=char.character_id,
                    character_name=char.character_name,
                    corpstats=cls.corpstat
                ) for char in cls.newchars
            ]
        )

        CorpMember.objects.create(
            character_id=cls.mainchar.character_id,
            character_name=cls.mainchar.character_name,
            corpstats=cls.corpstat
        )

    def test_get_corpstats(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                corputilsGetAllCorpstats {
                    corp {
                        id
                    }
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsGetAllCorpstats': [
                        {
                            'corp': {
                                'id': str(self.corp.pk)
                            }
                        }
                    ]
                }
            }
        )

    def test_get_corpstats_corp_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q($input: Int!) {
                corputilsGetCorpstatsCorp(corpId: $input) {
                    corp {
                        id
                    }
                }
            }
            ''',
            input_data=self.corp.corporation_id
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsGetCorpstatsCorp': {
                        'corp': {
                            'id': str(self.corp.pk)
                        }
                    }
                }
            }
        )

    def test_get_corpstats_corp_not_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q($input: Int!) {
                corputilsGetCorpstatsCorp(corpId: $input) {
                    corp {
                        id
                    }
                }
            }
            ''',
            input_data=self.corpstat2.corp.corporation_id
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsGetCorpstatsCorp': None
                }
            }
        )

    def test_search_corpstats(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q($input: String!) {
                corputilsSearchCorpstats(searchString: $input) {
                    characterId
                }
            }
            ''',
            input_data=self.mainchar.character_name
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsSearchCorpstats': [
                        {
                            'characterId': self.mainchar.character_id
                        }
                    ]
                }
            }
        )

    def test_character_field_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q($input: String!) {
                corputilsSearchCorpstats(searchString: $input) {
                    characterId
                    character {
                        id
                    }
                }
            }
            ''',
            input_data=self.mainchar.character_name
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsSearchCorpstats': [
                        {
                            'characterId': self.mainchar.character_id,
                            'character': {
                                'id': str(self.mainchar.pk)
                            }
                        }
                    ]
                }
            }
        )

    def test_character_field_not_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        max_char_id = CorpMember.objects.aggregate(m=Max('character_id'))['m']

        notregisteredmember = CorpMember.objects.create(
            character_id=max_char_id + 1,
            character_name=self.mainchar.character_name + ' 2',
            corpstats=self.corpstat
        )

        response = self.query(
            '''
            query q($input: String!) {
                corputilsSearchCorpstats(searchString: $input) {
                    characterId
                    character {
                        id
                    }
                }
            }
            ''',
            input_data=notregisteredmember.character_name
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsSearchCorpstats': [
                        {
                            'characterId': max_char_id + 1,
                            'character': None
                        }
                    ]
                }
            }
        )

    def test_registered_type(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                corputilsGetAllCorpstats {
                    registered {
                        id
                    }
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsGetAllCorpstats': [
                        {
                            'registered': [
                                {
                                    'id': str(self.mainchar.pk)
                                }
                            ]
                        }
                    ]
                }
            }
        )

    def test_unregistered_type(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                corputilsGetAllCorpstats {
                    unregistered {
                        id
                    }
                }
            }
            '''
        )

        expected = [str(char.pk) for char in self.newchars]

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertNotIn('errors', data)
        self.assertIn('corputilsGetAllCorpstats', data['data'])

        results = data['data']['corputilsGetAllCorpstats']

        self.assertEqual(len(results), 1)

        results = results[0]['unregistered']

        self.assertCountEqual(
            [r['id'] for r in results],
            expected
        )

    def test_mains_type(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                corputilsGetAllCorpstats {
                    mains {
                        id
                    }
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsGetAllCorpstats': [
                        {
                            'mains': [
                                {
                                    'id': str(self.mainchar.pk)
                                }
                            ]
                        }
                    ]
                }
            }
        )


class TestMutations(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory(main_character__scopes=['esi-corporations.read_corporation_membership.v1'])

        cls.user = AuthUtils.add_permission_to_user_by_name(
            'corputils.add_corpstats',
            cls.user,
            False
        )

        cls.token = cls.user.token_set.first()

    @patch('allianceauth.corputils.models.CorpStats.update')
    def test_add_corp_stats_mutation_ok(self, mock_update):
        mock_update.return_value = None

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                corputilsAddCorpstats(tokenId: $input) {
                    ok
                }
            }
            ''',
            input_data=self.token.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsAddCorpstats': {
                        'ok': True
                    }
                }
            }
        )

        self.assertTrue(mock_update.called)

    def test_add_corp_stats_mutation_wrong_user(self):
        user2 = UserMainFactory()

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                corputilsAddCorpstats(tokenId: $input) {
                    ok
                }
            }
            ''',
            input_data=user2.token_set.first().pk
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertIn('errors', data)
        self.assertIn('corputilsAddCorpstats', data['data'])
        self.assertIsNone(data['data']['corputilsAddCorpstats'])

        self.assertEqual(len(data['errors']), 1)

        error = data['errors'][0]

        self.assertIn('locations', error)
        self.assertIn('path', error)
        self.assertIn('message', error)

        self.assertEqual(error['path'], ['corputilsAddCorpstats'])

        self.assertEqual(error['message'], 'Token not valid')

    def test_add_corp_stats_mutation_token_missing(self):
        user2 = UserMainFactory()

        user2 = AuthUtils.add_permission_to_user_by_name(
            'corputils.add_corpstats',
            user2,
            False
        )

        self.client.force_login(user2, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                corputilsAddCorpstats(tokenId: $input) {
                    ok
                }
            }
            ''',
            input_data=user2.token_set.first().pk
        )

        data = json.loads(response.content)

        self.assertIn('data', data)
        self.assertIn('errors', data)
        self.assertIn('corputilsAddCorpstats', data['data'])
        self.assertIsNone(data['data']['corputilsAddCorpstats'])

        self.assertEqual(len(data['errors']), 1)

        error = data['errors'][0]

        self.assertIn('locations', error)
        self.assertIn('path', error)
        self.assertIn('message', error)

        self.assertEqual(error['path'], ['corputilsAddCorpstats'])

        self.assertEqual(error['message'], 'Required token missing')

    @patch('esi.models.Token.get_esi_client')
    @patch('allianceauth.corputils.models.CorpStats.update')
    def test_add_corp_stats_mutation_character_not_exists(self, mock_update, mock_esi_client):
        mock_update.return_value = None

        mock_endpoint = EsiEndpoint(
            'Character',
            'get_characters_character_id',
            'character_id',
            data={
                str(self.token.character_id): {
                    'corporation_id': self.user.profile.main_character.corporation_id
                }
            }
        )

        mock_esi_client.return_value = EsiClientStub.create_from_endpoints([mock_endpoint])

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        self.user.profile.main_character.delete()

        response = self.query(
            '''
            mutation m($input: ID!) {
                corputilsAddCorpstats(tokenId: $input) {
                    ok
                }
            }
            ''',
            input_data=self.token.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsAddCorpstats': {
                        'ok': True
                    }
                }
            }
        )

        self.assertTrue(mock_update.called)

    @patch('esi.clients.esi_client_factory')
    @patch('allianceauth.corputils.models.CorpStats.update')
    def test_add_corp_stats_mutation_corp_not_exists(self, mock_update, mock_esi_client):
        mock_update.return_value = None

        corp = self.user.profile.main_character.corporation

        mock_endpoint = EsiEndpoint(
            'Corporation',
            'get_corporations_corporation_id',
            'corporation_id',
            data={
                str(corp.corporation_id): {
                    'name': corp.corporation_name,
                    'ticker': corp.corporation_ticker,
                    'member_count': corp.member_count,
                    'alliance_id': corp.alliance_id,
                }
            }
        )

        mock_esi_client.return_value = EsiClientStub.create_from_endpoints([mock_endpoint])

        corp.delete()

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                corputilsAddCorpstats(tokenId: $input) {
                    ok
                }
            }
            ''',
            input_data=self.token.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsAddCorpstats': {
                        'ok': True
                    }
                }
            }
        )

        self.assertTrue(mock_update.called)

    @patch('allianceauth.corputils.models.CorpStats.update')
    def test_update_corpstats_ok(self, mock_update):
        mock_update.return_value = None

        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        corp = self.user.profile.main_character.corporation

        CorpStats.objects.create(
            token=self.token,
            corp=corp
        )

        response = self.query(
            '''
            mutation m($input: Int!) {
                corputilsUpdateCorpstats(corpId: $input) {
                    ok
                }
            }
            ''',
            input_data=corp.corporation_id
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'corputilsUpdateCorpstats': {
                        'ok': True
                    }
                }
            }
        )

        self.assertTrue(mock_update.called)
