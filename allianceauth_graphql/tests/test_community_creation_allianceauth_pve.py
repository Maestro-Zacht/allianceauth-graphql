import datetime
from graphene_django.utils.testing import GraphQLTestCase

from django.utils import timezone
from django.test import override_settings

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testdata_factories import UserMainFactory, EveCharacterFactory, UserFactory
from app_utils.testing import add_character_to_user, generate_invalid_pk

from allianceauth_pve.models import Rotation, Entry, EntryCharacter, EntryRole, PveButton

from ..community_creations.allianceauth_pve_integration.inputs import EntryInput


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'allianceauth_pve.access_pve',
                'allianceauth_pve.manage_entries',
                'allianceauth_pve.manage_rotations',
            ],
            UserMainFactory(),
            False
        )

        cls.mainchar = cls.user.profile.main_character

        cls.char2 = EveCharacterFactory()
        add_character_to_user(cls.user, cls.char2)

        cls.open_rotation: Rotation = Rotation.objects.create(name='Open Rotation')

        cls.closed_rotation: Rotation = Rotation.objects.create(
            name='Closed Rotation',
            is_closed=True,
            actual_total=100,
            closed_at=timezone.now() - datetime.timedelta(days=1),
        )

        cls.entry = Entry.objects.create(
            rotation=cls.closed_rotation,
            estimated_total=100,
            created_by=cls.user
        )

        role = EntryRole.objects.create(
            entry=cls.entry,
            name='Role',
            value=1
        )

        EntryCharacter.objects.create(
            entry=cls.entry,
            user=cls.user,
            user_character=cls.mainchar,
            role=role,
        )

    def test_pve_get_rotation(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($id: Int!) {
                pveGetRotation(id: $id) {
                    id
                    entries {
                        id
                    }
                    summary {
                        mainCharacter {
                            id
                        }
                    }
                }
            }
            ''',
            variables={'id': self.closed_rotation.pk},
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveGetRotation': {
                        'id': str(self.closed_rotation.pk),
                        'entries': [
                            {
                                'id': str(self.entry.pk),
                            }
                        ],
                        'summary': [
                            {
                                'mainCharacter': {
                                    'id': str(self.mainchar.pk),
                                }
                            }
                        ]
                    }
                }
            }
        )

    def test_pve_closed_rotations(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                pveClosedRotations {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveClosedRotations': [
                        {
                            'id': str(self.closed_rotation.pk),
                        }
                    ]
                }
            }
        )

    def test_pve_char_running_averages(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($start_date: Date!, $end_date: Date) {
                pveCharRunningAverages(startDate: $start_date, endDate: $end_date) {
                    actualTotal
                    estimatedTotal
                    mainCharacter {
                        id
                    }
                }
            }
            ''',
            variables={'start_date': '2020-01-01'},
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveCharRunningAverages': {
                        'actualTotal': 100.0,
                        'estimatedTotal': 100.0,
                        'mainCharacter': None,
                    },
                }
            }
        )

    def test_pve_active_rotations(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                pveActiveRotations {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveActiveRotations': [
                        {
                            'id': str(self.open_rotation.pk),
                        }
                    ]
                }
            }
        )

    def test_pve_search_rotation_characters_all(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($name: String, $excludeCharactersIds: [Int!]) {
                pveSearchRotationCharacters(name: $name, excludeCharactersIds: $excludeCharactersIds) {
                    id
                }
            }
            ''',
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveSearchRotationCharacters': [
                        {
                            'id': str(self.mainchar.pk),
                        },
                        {
                            'id': str(self.char2.pk),
                        }
                    ]
                }
            }
        )

    def test_pve_search_rotation_characters_name(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($name: String, $excludeCharactersIds: [Int!]) {
                pveSearchRotationCharacters(name: $name, excludeCharactersIds: $excludeCharactersIds) {
                    id
                }
            }
            ''',
            variables={
                'name': self.char2.character_name
            },
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveSearchRotationCharacters': [
                        {
                            'id': str(self.mainchar.pk),
                        },
                        {
                            'id': str(self.char2.pk),
                        },
                    ]
                }
            }
        )

    @override_settings(PVE_ONLY_MAINS=True)
    def test_pve_search_rotation_characters_name_only_mains(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($name: String, $excludeCharactersIds: [Int!]) {
                pveSearchRotationCharacters(name: $name, excludeCharactersIds: $excludeCharactersIds) {
                    id
                }
            }
            ''',
            variables={'name': self.char2.character_name},
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveSearchRotationCharacters': [
                        {
                            'id': str(self.mainchar.pk),
                        }
                    ]
                }
            }
        )

    def test_pve_search_rotation_characters_exclude(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($name: String, $excludeCharactersIds: [Int!]) {
                pveSearchRotationCharacters(name: $name, excludeCharactersIds: $excludeCharactersIds) {
                    id
                }
            }
            ''',
            variables={'excludeCharactersIds': [self.mainchar.pk]},
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveSearchRotationCharacters': [
                        {
                            'id': str(self.char2.pk),
                        }
                    ]
                }
            }
        )

    def test_pve_roles_setups(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                pveRolesSetups {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveRolesSetups': []
                }
            }
        )

    def test_pve_buttons(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                pveButtons {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveButtons': [
                        {
                            'id': str(button.pk),
                        } for button in PveButton.objects.all()
                    ]
                }
            }
        )


class TestEntryInput(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()
        cls.mainchar = cls.user.profile.main_character

        cls.user2 = UserMainFactory()
        cls.mainchar2 = cls.user2.profile.main_character

        cls.input_data = {
            'roles': [
                {
                    'name': 'role1',
                    'value': 1,
                }
            ],
            'shares': [
                {
                    'character_id': cls.mainchar.pk,
                    'user_id': cls.user.pk,
                    'site_count': 1,
                    'role': 'role1',
                },
                {
                    'character_id': cls.mainchar2.pk,
                    'user_id': cls.user2.pk,
                    'site_count': 1,
                    'role': 'role1',
                }
            ]
        }

    def test_ok(self):
        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))
        self.assertEqual(errors, [])

    def test_duplicated_roles(self):
        self.input_data['roles'].append(self.input_data['roles'][0])

        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))

        self.assertEqual(errors, [f"{self.input_data['roles'][0]['name']} name is not unique"])

    def test_duplicated_character(self):
        self.input_data['shares'].append(self.input_data['shares'][0])

        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))

        self.assertEqual(errors, [f"character {self.input_data['shares'][0]['character_id']} cannot have more than 1 share"])

    def test_invalid_role(self):
        self.input_data['shares'][0]['role'] = 'invalid'

        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))

        self.assertEqual(errors, [f"{self.input_data['shares'][0]['role']} is not a valid role"])

    def test_wrong_ownership(self):
        self.input_data['shares'][0]['user_id'] = self.user2.pk

        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))

        self.assertEqual(errors, ["character ownership doesn't match"])

    def test_invalid_total(self):
        self.input_data['shares'][0]['site_count'] = 0
        self.input_data['shares'][1]['site_count'] = 0

        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))

        self.assertEqual(errors, ["Form not valid, you need at least 1 person to receive loot"])

    def test_no_roles_or_shares(self):
        self.input_data['roles'] = []
        self.input_data['shares'] = []

        errors = EntryInput.is_valid(type('EntryInput', (object,), self.input_data))

        self.assertEqual(errors, ["Form not valid, you need at least 1 person to receive loot", "Not enough shares or roles"])


class TestCreateRattingEntry(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'allianceauth_pve.access_pve',
                'allianceauth_pve.manage_entries',
                'allianceauth_pve.manage_rotations',
            ],
            UserMainFactory(),
            False
        )

        cls.mainchar = cls.user.profile.main_character

        cls.char2 = EveCharacterFactory()
        add_character_to_user(cls.user, cls.char2)

        cls.rotation: Rotation = Rotation.objects.create(name='Open Rotation')

        cls.input_data = {
            'estimatedTotal': 1000,
            'roles': [
                {
                    'name': 'role2',
                    'value': 1,
                }
            ],
            'shares': [
                {
                    'characterId': cls.mainchar.pk,
                    'userId': cls.user.pk,
                    'siteCount': 1,
                    'role': 'role2',
                },
                {
                    'characterId': cls.char2.pk,
                    'userId': cls.user.pk,
                    'siteCount': 1,
                    'role': 'role2',
                    'helpedSetup': True,
                }
            ]
        }

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: EntryInput!, $rotationId: Int!) {
                pveCreateEntry(input: $input, rotationId: $rotationId) {
                    ok
                    errors
                }
            }
            ''',
            variables={
                'input': self.input_data,
                'rotationId': self.rotation.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveCreateEntry': {
                        'ok': True,
                        'errors': [],
                    }
                }
            }
        )

        self.assertEqual(Entry.objects.count(), 1)

    def test_invalid_rotation(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: EntryInput!, $rotationId: Int!) {
                pveCreateEntry(input: $input, rotationId: $rotationId) {
                    ok
                    errors
                }
            }
            ''',
            variables={
                'input': self.input_data,
                'rotationId': generate_invalid_pk(Rotation),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveCreateEntry': {
                        'ok': False,
                        'errors': ["Rotation doesn't exists"],
                    }
                }
            }
        )

        self.assertEqual(Entry.objects.count(), 0)


class TestModifyRattingEntry(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'allianceauth_pve.access_pve',
                'allianceauth_pve.manage_entries',
                'allianceauth_pve.manage_rotations',
            ],
            UserMainFactory(),
            False
        )

        cls.mainchar = cls.user.profile.main_character

        cls.char2 = EveCharacterFactory()
        add_character_to_user(cls.user, cls.char2)

        cls.user2 = UserFactory()

        cls.rotation: Rotation = Rotation.objects.create(name='Open Rotation')

        cls.entry = Entry.objects.create(
            rotation=cls.rotation,
            estimated_total=100,
            created_by=cls.user
        )

        role = EntryRole.objects.create(
            entry=cls.entry,
            name='Role',
            value=1
        )

        EntryCharacter.objects.create(
            entry=cls.entry,
            user=cls.user,
            user_character=cls.mainchar,
            role=role,
        )

        cls.input_data = {
            'estimatedTotal': 1000,
            'roles': [
                {
                    'name': 'role2',
                    'value': 1,
                }
            ],
            'shares': [
                {
                    'characterId': cls.mainchar.pk,
                    'userId': cls.user.pk,
                    'siteCount': 1,
                    'role': 'role2',
                },
                {
                    'characterId': cls.char2.pk,
                    'userId': cls.user.pk,
                    'siteCount': 1,
                    'role': 'role2',
                    'helpedSetup': True,
                }
            ]
        }

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: EntryInput!, $entryId: Int!) {
                pveModifyEntry(input: $input, entryId: $entryId) {
                    ok
                    errors
                    entry {
                        id
                        estimatedTotal
                    }
                }
            }
            ''',
            variables={
                'input': self.input_data,
                'entryId': self.entry.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveModifyEntry': {
                        'ok': True,
                        'errors': [],
                        'entry': {
                            'id': str(self.entry.pk),
                            'estimatedTotal': 1000,
                        }
                    }
                }
            }
        )

        self.assertEqual(Entry.objects.count(), 1)
        self.assertEqual(self.entry.ratting_shares.count(), 2)

    def test_cannot_edit(self):
        self.client.force_login(self.user)

        self.rotation.is_closed = True
        self.rotation.save()

        response = self.query(
            '''
            mutation($input: EntryInput!, $entryId: Int!) {
                pveModifyEntry(input: $input, entryId: $entryId) {
                    ok
                    errors
                }
            }
            ''',
            variables={
                'input': self.input_data,
                'entryId': self.entry.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveModifyEntry': {
                        'ok': False,
                        'errors': ["You cannot edit this entry"],
                    }
                }
            }
        )


class TestDeleteRattingEntry(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'allianceauth_pve.access_pve',
                'allianceauth_pve.manage_entries',
                'allianceauth_pve.manage_rotations',
            ],
            UserMainFactory(),
            False
        )

        cls.mainchar = cls.user.profile.main_character

        cls.user2 = UserFactory()

        cls.rotation: Rotation = Rotation.objects.create(name='Open Rotation')

        cls.entry = Entry.objects.create(
            rotation=cls.rotation,
            estimated_total=100,
            created_by=cls.user
        )

        role = EntryRole.objects.create(
            entry=cls.entry,
            name='Role',
            value=1
        )

        EntryCharacter.objects.create(
            entry=cls.entry,
            user=cls.user,
            user_character=cls.mainchar,
            role=role,
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($entryId: Int!) {
                pveDeleteEntry(entryId: $entryId) {
                    ok
                }
            }
            ''',
            variables={
                'entryId': self.entry.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveDeleteEntry': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(Entry.objects.count(), 0)

    def test_cannot_delete(self):
        self.client.force_login(self.user)

        self.rotation.is_closed = True
        self.rotation.save()

        response = self.query(
            '''
            mutation($entryId: Int!) {
                pveDeleteEntry(entryId: $entryId) {
                    ok
                }
            }
            ''',
            variables={
                'entryId': self.entry.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveDeleteEntry': {
                        'ok': False,
                    }
                }
            }
        )

        self.assertEqual(Entry.objects.count(), 1)


class TestCreateRotation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'allianceauth_pve.access_pve',
                'allianceauth_pve.manage_rotations',
            ],
            UserMainFactory(),
            False
        )

        cls.mainchar = cls.user.profile.main_character

        cls.user2 = UserFactory()

        cls.input_data = {
            'name': 'Test Rotation',
            'priority': 1,
            'taxRate': 10.0,
            'maxDailySetups': 1,
            'minPeopleShareSetup': 3
        }

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: CreateRotationInput!) {
                pveCreateRotation(input: $input) {
                    rotation {
                        name
                    }
                }
            }
            ''',
            variables={
                'input': self.input_data,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveCreateRotation': {
                        'rotation': {
                            'name': 'Test Rotation',
                        }
                    }
                }
            }
        )

        self.assertEqual(Rotation.objects.count(), 1)


class TestCloseRotation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'allianceauth_pve.access_pve',
                'allianceauth_pve.manage_rotations',
            ],
            UserMainFactory(),
            False
        )

        cls.mainchar = cls.user.profile.main_character

        cls.user2 = UserFactory()

        cls.rotation: Rotation = Rotation.objects.create(name='Open Rotation')

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: RotationCloseInput!) {
                pveCloseRotation(input: $input) {
                    ok
                }
            }
            ''',
            input_data={
                'rotationId': self.rotation.pk,
                'salesValue': 0,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveCloseRotation': {
                        'ok': True,
                    }
                }
            }
        )

        self.rotation.refresh_from_db()
        self.assertTrue(self.rotation.is_closed)

    def test_already_closed(self):
        self.client.force_login(self.user)

        self.rotation.is_closed = True
        self.rotation.save()

        response = self.query(
            '''
            mutation($input: RotationCloseInput!) {
                pveCloseRotation(input: $input) {
                    ok
                }
            }
            ''',
            input_data={
                'rotationId': self.rotation.pk,
                'salesValue': 0,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'pveCloseRotation': {
                        'ok': False,
                    }
                }
            }
        )

        self.rotation.refresh_from_db()
        self.assertTrue(self.rotation.is_closed)
