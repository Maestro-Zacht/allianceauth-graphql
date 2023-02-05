from datetime import timedelta

from graphene_django.utils.testing import GraphQLTestCase
from unittest.mock import patch

from django.utils import timezone
from django.core.exceptions import ValidationError

from allianceauth.tests.test_auth_utils import AuthUtils
from app_utils.testdata_factories import UserMainFactory, EveCharacterFactory, UserFactory
from app_utils.testing import add_character_to_user, generate_invalid_pk
from app_utils.esi_testing import EsiEndpoint, EsiClientStub

from allianceauth.fleetactivitytracking.models import Fatlink, Fat
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from esi.models import Token


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'auth.fleetactivitytracking_statistics',
                'auth.fleetactivitytracking',
            ],
            cls.user,
            False
        )

        cls.corp: EveCorporationInfo = cls.user.profile.main_character.corporation

        cls.extrachar1, *charlist = EveCharacterFactory.create_batch(7, corporation=cls.corp)

        cls.user2 = UserMainFactory(main_character__character=cls.extrachar1)

        for char in charlist:
            add_character_to_user(cls.user2, char)

        cls.fatlink = Fatlink.objects.create(
            creator=cls.user,
            fatdatetime=timezone.now(),
            fleet='Test Fatlink',
            hash='testhash',
            duration=60,
        )

        for char in EveCharacter.objects.select_related('character_ownership__user').all():
            Fat.objects.create(
                character=char,
                fatlink=cls.fatlink,
                shiptype='Test Ship',
                system='Test System',
                station='Test Station',
                user=char.character_ownership.user,
            )

    def test_recent_fats(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                fatRecentFat {
                    id
                }
            }
            ''',
        )

        fat = Fat.objects.get(user=self.user)

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatRecentFat': [
                        {
                            'id': str(fat.id),
                        }
                    ]
                }
            }
        )

    def test_fatlinks(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                fatGetFatlinks {
                    id
                }
            }
            ''',
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatGetFatlinks': [
                        {
                            'id': str(self.fatlink.id),
                        }
                    ]
                }
            }
        )

    def test_fat_corp_monthly_stats(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($year: Int!, $month: Int!, $corpId: Int!) {
                fatCorpMonthlyStats(year: $year, month: $month, corpId: $corpId) {
                    user {
                        id
                    }
                    numChars
                }
            }
            ''',
            variables={
                'year': timezone.now().year,
                'month': timezone.now().month,
                'corpId': self.corp.corporation_id
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatCorpMonthlyStats': [
                        {
                            'user': {
                                'id': str(self.user2.id),
                            },
                            'numChars': 7,
                        },
                        {
                            'user': {
                                'id': str(self.user.id),
                            },
                            'numChars': 1,
                        },
                    ]
                }
            }
        )

    def test_fat_general_monthly_stats(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($year: Int!, $month: Int!) {
                fatGeneralMonthlyStats(year: $year, month: $month) {
                    corporation {
                        id
                    }
                    numFats
                }
            }
            ''',
            variables={
                'year': timezone.now().year,
                'month': timezone.now().month,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatGeneralMonthlyStats': [
                        {
                            'corporation': {
                                'id': str(self.corp.id),
                            },
                            'numFats': 8,
                        }
                    ]
                }
            }
        )

    def test_fat_personal_stats(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                fatPersonalStats {
                    month
                    year
                    numFats
                }
            }
            ''',
        )

        fat = Fat.objects.select_related('fatlink').get(user=self.user)

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatPersonalStats': [
                        {
                            'month': fat.fatlink.fatdatetime.month,
                            'year': fat.fatlink.fatdatetime.year,
                            'numFats': 1,
                        }
                    ]
                }
            }
        )

    def test_fat_personal_monthly_stats_self(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($year: Int!, $month: Int!, $charId: Int) {
                fatPersonalMonthlyStats(year: $year, month: $month, charId: $charId) {
                    collectedLinks {
                        shiptype
                        timesUsed
                    }
                    createdLinks {
                        id
                    }
                }
            }
            ''',
            variables={
                'year': timezone.now().year,
                'month': timezone.now().month,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatPersonalMonthlyStats': {
                        'collectedLinks': [
                            {
                                'shiptype': 'Test Ship',
                                'timesUsed': 1,
                            }
                        ],
                        'createdLinks': [
                            {
                                'id': str(self.fatlink.id),
                            }
                        ]
                    }
                }
            }
        )

    def test_fat_personal_monthly_stats_other(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($year: Int!, $month: Int!, $charId: Int) {
                fatPersonalMonthlyStats(year: $year, month: $month, charId: $charId) {
                    collectedLinks {
                        shiptype
                        timesUsed
                    }
                    createdLinks {
                        id
                    }
                }
            }
            ''',
            variables={
                'year': timezone.now().year,
                'month': timezone.now().month,
                'charId': self.extrachar1.character_id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatPersonalMonthlyStats': {
                        'collectedLinks': [
                            {
                                'shiptype': 'Test Ship',
                                'timesUsed': 7,
                            }
                        ],
                        'createdLinks': []
                    }
                }
            }
        )


class TestAddFatParticipationMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.scopes = [
            'esi-location.read_location.v1',
            'esi-location.read_ship_type.v1',
            'esi-universe.read_structures.v1',
            'esi-location.read_online.v1',
        ]

        cls.user = UserMainFactory(
            main_character__scopes=cls.scopes
        )
        cls.token1 = cls.user.token_set.first()
        cls.mainchar = cls.user.profile.main_character

        cls.char2 = EveCharacterFactory()
        add_character_to_user(cls.user, cls.char2, scopes=cls.scopes)
        cls.token2 = cls.user.token_set.get(character_id=cls.char2.character_id)

        cls.fatlink = Fatlink.objects.create(
            creator=cls.user,
            fatdatetime=timezone.now(),
            fleet='Test Fatlink',
            hash='testhash',
            duration=60,
        )

        cls.endpoints = [
            EsiEndpoint(
                'Location',
                'get_characters_character_id_online',
                'character_id',
            ),
            EsiEndpoint(
                'Location',
                'get_characters_character_id_location',
                'character_id',
            ),
            EsiEndpoint(
                'Location',
                'get_characters_character_id_ship',
                'character_id',
            ),
            EsiEndpoint(
                'Universe',
                'get_universe_systems_system_id',
                'system_id',
            ),
            EsiEndpoint(
                'Universe',
                'get_universe_stations_station_id',
                'station_id',
            ),
            EsiEndpoint(
                'Universe',
                'get_universe_structures_structure_id',
                'structure_id',
            )
        ]

        cls.data = {
            'Location': {
                'get_characters_character_id_online': {
                    str(cls.mainchar.character_id): {
                        'online': True,
                    },
                    str(cls.char2.character_id): {
                        'online': False,
                    },
                },
                'get_characters_character_id_location': {
                    str(cls.mainchar.character_id): {
                        'solar_system_id': 30000142,
                        'station_id': None,
                        'structure_id': None,
                    }
                },
                'get_characters_character_id_ship': {
                    str(cls.mainchar.character_id): {
                        'ship_type_id': 123,
                    }
                }
            },
            'Universe': {
                'get_universe_systems_system_id': {
                    '30000142': {
                        'name': 'Jita',
                    }
                },
                'get_universe_stations_station_id': {
                    '123456789': {
                        'name': 'Test Station',
                    }
                },
                'get_universe_structures_structure_id': {
                    '1234567890': {
                        'name': 'Test Structure',
                    }
                }
            }
        }

    def test_token_missing(self):
        user2 = UserMainFactory()
        self.client.force_login(user2)

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': None
                },
                'errors': [
                    {
                        'message': 'Required token missing',
                        'locations': [
                            {
                                'line': 3,
                                'column': 17
                            }
                        ],
                        'path': [
                            'fatParticipateToFatlink'
                        ]
                    }
                ]
            }
        )

        self.assertEqual(Fat.objects.count(), 0)

    @patch('allianceauth_graphql.fleetactivitytracking.mutations.provider.get_itemtype')
    @patch('esi.models.Token.get_esi_client')
    def test_ok(self, mock_get_esi_client, mock_get_itemtype):
        self.client.force_login(self.user)

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)
        mock_get_itemtype.return_value = type('Item', (object,), {'name': 'Test Ship'})

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': True,
                        'error': None,
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 1)

        fat = Fat.objects.first()

        self.assertEqual(fat.station, "No Station")

    def test_invalid_token(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': generate_invalid_pk(Token),
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': False,
                        'error': 'Token not valid',
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 0)

    @patch('esi.models.Token.get_esi_client')
    def test_character_not_online(self, mock_get_esi_client):
        self.client.force_login(self.user)

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token2.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': False,
                        'error': f"Cannot register the fleet participation for {self.char2.character_name}. The character needs to be online.",
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 0)

    @patch('esi.models.Token.get_esi_client')
    def test_fatlink_expired(self, mock_get_esi_client):
        self.client.force_login(self.user)

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)

        self.fatlink.fatdatetime = timezone.now() - timedelta(minutes=self.fatlink.duration * 2)
        self.fatlink.save()

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': False,
                        'error': 'FAT link has expired or user not valid',
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 0)

    @patch('esi.models.Token.get_esi_client')
    def test_character_not_exists(self, mock_get_esi_client):
        self.client.force_login(self.user)

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)

        self.mainchar.delete()

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': False,
                        'error': "Character doesn't exists",
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 0)

    @patch('allianceauth_graphql.fleetactivitytracking.mutations.provider.get_itemtype')
    @patch('esi.models.Token.get_esi_client')
    def test_in_station(self, mock_get_esi_client, mock_get_itemtype):
        self.client.force_login(self.user)

        self.data['Location']['get_characters_character_id_location'][str(self.mainchar.character_id)]['station_id'] = 123456789

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)
        mock_get_itemtype.return_value = type('Item', (object,), {'name': 'Test Ship'})

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': True,
                        'error': None,
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 1)

        fat = Fat.objects.first()

        self.assertEqual(fat.station, 'Test Station')

    @patch('allianceauth_graphql.fleetactivitytracking.mutations.provider.get_itemtype')
    @patch('esi.models.Token.get_esi_client')
    def test_in_structure(self, mock_get_esi_client, mock_get_itemtype):
        self.client.force_login(self.user)

        self.data['Location']['get_characters_character_id_location'][str(self.mainchar.character_id)]['structure_id'] = 1234567890

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)
        mock_get_itemtype.return_value = type('Item', (object,), {'name': 'Test Ship'})

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': True,
                        'error': None,
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 1)

        fat = Fat.objects.first()

        self.assertEqual(fat.station, 'Test Structure')

    @patch('allianceauth.fleetactivitytracking.models.Fat.full_clean')
    @patch('allianceauth_graphql.fleetactivitytracking.mutations.provider.get_itemtype')
    @patch('esi.models.Token.get_esi_client')
    def test_validation_error(self, mock_get_esi_client, mock_get_itemtype, mock_full_clean):
        self.client.force_login(self.user)

        mock_get_esi_client.return_value = EsiClientStub(self.data, self.endpoints)
        mock_get_itemtype.return_value = type('Item', (object,), {'name': 'Test Ship'})
        mock_full_clean.side_effect = ValidationError({'test': 'Test Error'})

        response = self.query(
            '''
            mutation($tokenId: ID!, $fatlinkHash: String!) {
                fatParticipateToFatlink(tokenId: $tokenId, fatlinkHash: $fatlinkHash) {
                    ok
                    error
                }
            }
            ''',
            variables={
                'tokenId': self.token1.id,
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatParticipateToFatlink': {
                        'ok': False,
                        'error': 'Test Error',
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 0)


class TestCreateFatlinkMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.fleetactivitytracking', UserFactory(), False)

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: CreateFatlinkInput!) {
                fatCreateFatlink(input: $input) {
                    ok
                }
            }
            ''',
            input_data={
                'fleet': 'Test Fleet',
                'duration': 60,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatCreateFatlink': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(Fatlink.objects.count(), 1)

        fatlink = Fatlink.objects.first()

        self.assertEqual(fatlink.fleet, 'Test Fleet')
        self.assertEqual(fatlink.duration, 60)


class TestOtherMutations(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.fleetactivitytracking', UserMainFactory(), False)

        cls.mainchar = cls.user.profile.main_character

        cls.fatlink = Fatlink.objects.create(
            creator=cls.user,
            fatdatetime=timezone.now(),
            fleet='Test Fatlink',
            hash='testhash',
            duration=60,
        )

        cls.fat = Fat.objects.create(
            fatlink=cls.fatlink,
            character=cls.mainchar,
            shiptype='Test Ship',
            system='Test System',
            station='Test Station',
            user=cls.user,
        )

    def test_remove_char_fatlink(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fatlinkHash: String!, $characterId: Int!) {
                fatRemoveCharFat(fatlinkHash: $fatlinkHash, characterId: $characterId) {
                    ok
                }
            }
            ''',
            variables={
                'fatlinkHash': self.fatlink.hash,
                'characterId': self.mainchar.character_id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatRemoveCharFat': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(Fat.objects.count(), 0)

    def test_delete_fatlink(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($fatlinkHash: String!) {
                fatDeleteFatlink(fatlinkHash: $fatlinkHash) {
                    ok
                }
            }
            ''',
            variables={
                'fatlinkHash': self.fatlink.hash,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'fatDeleteFatlink': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(Fatlink.objects.count(), 0)
