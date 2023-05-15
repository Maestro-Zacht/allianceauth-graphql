from graphene_django.utils.testing import GraphQLTestCase

from allianceauth.notifications import notify
from allianceauth.notifications.models import Notification

from app_utils.testdata_factories import UserFactory


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        notify(cls.user, "Test notif 1", level="success")

        cls.notif1: Notification = Notification.objects.get(title="Test notif 1")

        notify(cls.user, "Test notif 2", level="warning")

        cls.notif2: Notification = Notification.objects.get(title="Test notif 2")

        cls.notif1.viewed = True
        cls.notif1.save()

    def test_notif_read_list(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                notifReadList {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifReadList': [
                        {
                            'id': str(self.notif1.pk)
                        }
                    ]
                }
            }
        )

    def test_notif_unread_list(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                notifUnreadList {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifUnreadList': [
                        {
                            'id': str(self.notif2.pk)
                        }
                    ]
                }
            }
        )

    def test_notif_unread_count_user_pk(self):
        response = self.query(
            '''
            query q($input: ID!) {
                notifUnreadCount(userPk: $input)
            }
            ''',
            input_data=self.user.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifUnreadCount': 1
                }
            }
        )

    def test_notif_unread_count_login(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            query q {
                notifUnreadCount
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifUnreadCount': 1
                }
            }
        )

    def test_notif_unread_count_error(self):
        response = self.query(
            '''
            query q {
                notifUnreadCount
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifUnreadCount': -1
                }
            }
        )


class TestMutations(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()

        notify(cls.user, "Test notif 1", level="success")

        cls.notif1: Notification = Notification.objects.get(title="Test notif 1")

        notify(cls.user, "Test notif 2", level="warning")

        cls.notif2: Notification = Notification.objects.get(title="Test notif 2")

    def test_mark_read_mutation_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                notifMarkAsRead(notifId: $input) {
                    notification {
                        id
                        viewed
                    }
                }
            }
            ''',
            input_data=self.notif1.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifMarkAsRead': {
                        'notification': {
                            'id': str(self.notif1.pk),
                            'viewed': True
                        }
                    }
                }
            }
        )

    def test_mark_read_mutation_not_ok(self):
        self.client.force_login(self.user2, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                notifMarkAsRead(notifId: $input) {
                    ok
                    notification {
                        id
                        viewed
                    }
                }
            }
            ''',
            input_data=self.notif1.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifMarkAsRead': {
                        'notification': None,
                        'ok': False
                    }
                }
            }
        )

    def test_delete_mutation_ok(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                notifDelete(notifId: $input) {
                    ok
                }
            }
            ''',
            input_data=self.notif1.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifDelete': {
                        'ok': True
                    }
                }
            }
        )

        self.assertFalse(
            Notification.objects
            .filter(pk=self.notif1.pk)
            .exists()
        )

    def test_delete_mutation_not_ok(self):
        self.client.force_login(self.user2, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m($input: ID!) {
                notifDelete(notifId: $input) {
                    ok
                }
            }
            ''',
            input_data=self.notif1.pk
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifDelete': {
                        'ok': False
                    }
                }
            }
        )

        self.assertTrue(
            Notification.objects
            .filter(pk=self.notif1.pk)
            .exists()
        )

    def test_all_read(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        response = self.query(
            '''
            mutation m {
                notifMarkAllRead {
                    ok
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifMarkAllRead': {
                        'ok': True
                    }
                }
            }
        )

        self.assertFalse(
            Notification.objects
            .filter(user=self.user, viewed=False)
            .exists()
        )

        self.assertEqual(
            Notification.objects
            .filter(user=self.user, viewed=True)
            .count(),
            2
        )

    def test_delete_all_read(self):
        self.client.force_login(self.user, "graphql_jwt.backends.JSONWebTokenBackend")

        self.notif1.viewed = True
        self.notif1.save()

        response = self.query(
            '''
            mutation m {
                notifDeleteAllRead {
                    ok
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'notifDeleteAllRead': {
                        'ok': True
                    }
                }
            }
        )

        self.assertFalse(
            Notification.objects
            .filter(pk=self.notif1.pk)
            .exists()
        )

        self.assertTrue(
            Notification.objects
            .filter(pk=self.notif2.pk)
            .exists()
        )
