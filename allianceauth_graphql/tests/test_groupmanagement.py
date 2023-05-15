from graphene_django.utils.testing import GraphQLTestCase
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import override_settings

from allianceauth.tests.test_auth_utils import AuthUtils
from app_utils.testdata_factories import UserFactory
from app_utils.testing import generate_invalid_pk

from allianceauth.groupmanagement.models import GroupRequest, RequestLog

from ..groupmanagement.types import GroupRequestLogType, GroupRequestLogActionType, GroupRequestAddStatus, GroupRequestLeaveStatus
from ..authentication.types import GroupStatusEnum


class TestQueries(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.group_management', UserFactory(), False)

        cls.user2 = UserFactory()

        cls.group1 = Group.objects.create(name="Test Group 1")

        cls.authgroup1 = cls.group1.authgroup

        cls.authgroup1.internal = False
        cls.authgroup1.open = False
        cls.authgroup1.hidden = False
        cls.authgroup1.public = True
        cls.authgroup1.save()

        cls.group2 = Group.objects.create(name="Test Group 2")

        cls.authgroup2 = cls.group2.authgroup

        cls.authgroup2.internal = False
        cls.authgroup2.open = False
        cls.authgroup2.hidden = False
        cls.authgroup2.public = True
        cls.authgroup2.save()

        cls.user2.groups.add(cls.group2)
        cls.authgroup2.group_leaders.add(cls.user2)

        GroupRequest.objects.create(
            user=cls.user,
            group=cls.group1,
            leave_request=False,
        )

        cls.user3 = UserFactory()
        cls.user3.groups.add(cls.group2)

        GroupRequest.objects.create(
            user=cls.user3,
            group=cls.group2,
            leave_request=True,
        )

        cls.log1 = RequestLog.objects.create(
            request_type=None,
            group=cls.group1,
            request_info=f'{cls.user2.username}:{cls.group1.name}',
            action=False,
            request_actor=cls.user,
        )

        cls.log2 = RequestLog.objects.create(
            request_type=True,
            group=cls.group1,
            request_info=f'{cls.user2.username}:{cls.group1.name}',
            action=True,
            request_actor=cls.user,
        )

        cls.log3 = RequestLog.objects.create(
            request_type=False,
            group=cls.group1,
            request_info=f'{cls.user2.username}:{cls.group1.name}',
            action=False,
            request_actor=cls.user,
        )

    def test_user_joinable_groups(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                groupmanagementUserJoinableGroups {
                    id
                    status
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementUserJoinableGroups": [
                        {
                            "id": str(self.group1.id),
                            "status": GroupStatusEnum.PENDING.name,
                        },
                        {
                            "id": str(self.group2.id),
                            "status": GroupStatusEnum.CAN_APPLY.name,
                        },
                    ]
                }
            }
        )

    def test_group_management_has_perms(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                groupmanagementManageRequests {
                    leaveRequests {
                        group {
                            id
                        }
                        user {
                            id
                        }
                    }
                    acceptRequests {
                        group {
                            id
                        }
                        user {
                            id
                        }
                    }
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementManageRequests": {
                        "leaveRequests": [
                            {
                                "group": {
                                    "id": str(self.group2.id),
                                },
                                "user": {
                                    "id": str(self.user3.id),
                                }
                            }
                        ],
                        "acceptRequests": [
                            {
                                "group": {
                                    "id": str(self.group1.id),
                                },
                                "user": {
                                    "id": str(self.user.id),
                                }
                            }
                        ]
                    }
                }
            }
        )

    def test_group_management_group_leader(self):
        self.client.force_login(self.user2)

        response = self.query(
            '''
            query {
                groupmanagementManageRequests {
                    leaveRequests {
                        group {
                            id
                        }
                        user {
                            id
                        }
                    }
                    acceptRequests {
                        group {
                            id
                        }
                        user {
                            id
                        }
                    }
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementManageRequests": {
                        "leaveRequests": [
                            {
                                "group": {
                                    "id": str(self.group2.id),
                                },
                                "user": {
                                    "id": str(self.user3.id),
                                }
                            }
                        ],
                        "acceptRequests": []
                    }
                }
            }
        )

    def test_group_membership_has_perms(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                groupmanagementGroups {
                    id
                    numMembers
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroups": [
                        {
                            "id": str(self.group1.id),
                            "numMembers": 0,
                        },
                        {
                            "id": str(self.group2.id),
                            "numMembers": 2,
                        },
                    ]
                }
            }
        )

    def test_group_membership_group_leader(self):
        self.client.force_login(self.user2)

        response = self.query(
            '''
            query {
                groupmanagementGroups {
                    id
                    numMembers
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroups": [
                        {
                            'id': str(self.group2.id),
                            'numMembers': 2,
                        }
                    ]
                }
            }
        )

    def test_group_membership_list_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($groupId: Int!) {
                groupmanagementGroupMemberships(groupId: $groupId) {
                    group {
                        id
                    }
                    members {
                        user {
                            id
                        }
                        isLeader
                    }
                }
            }
            ''',
            variables={
                "groupId": self.group2.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroupMemberships": {
                        'group': {
                            'id': str(self.group2.id),
                        },
                        "members": [
                            {
                                "user": {
                                    "id": str(user.id),
                                },
                                "isLeader": user == self.user2,
                            } for user in [self.user2, self.user3]
                        ]
                    }
                }
            }
        )

    def test_group_membership_list_permission_denied(self):
        self.client.force_login(self.user2)

        response = self.query(
            '''
            query($groupId: Int!) {
                groupmanagementGroupMemberships(groupId: $groupId) {
                    group {
                        id
                    }
                    members {
                        user {
                            id
                        }
                        isLeader
                    }
                }
            }
            ''',
            variables={
                "groupId": self.group1.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroupMemberships": None
                },
                "errors": [
                    {
                        "message": 'An unknown error occurred.',
                        "locations": [
                            {
                                "line": 3,
                                "column": 17
                            }
                        ],
                        "path": [
                            "groupmanagementGroupMemberships"
                        ]
                    }
                ]
            }
        )

    def test_group_membership_list_not_found(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($groupId: Int!) {
                groupmanagementGroupMemberships(groupId: $groupId) {
                    group {
                        id
                    }
                    members {
                        user {
                            id
                        }
                        isLeader
                    }
                }
            }
            ''',
            variables={
                "groupId": generate_invalid_pk(Group),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroupMemberships": None
                },
                "errors": [
                    {
                        "message": "Group doesn't exist",
                        "locations": [
                            {
                                "line": 3,
                                "column": 17
                            }
                        ],
                        "path": [
                            "groupmanagementGroupMemberships"
                        ]
                    }
                ]
            }
        )

    def test_group_membership_audit_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($groupId: Int!) {
                groupmanagementGroupMembershipAudit(groupId: $groupId) {
                    group {
                        id
                    }
                    entries {
                        requestType
                        action
                        requestor {
                            id
                        }
                    }
                }
            }
            ''',
            variables={
                "groupId": self.group1.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroupMembershipAudit": {
                        'group': {
                            'id': str(self.group1.id),
                        },
                        "entries": [
                            {
                                "requestType": GroupRequestLogType.JOIN.name,
                                "action": GroupRequestLogActionType.REJECT.name,
                                "requestor": {
                                    "id": str(self.user2.id),
                                }
                            },
                            {
                                "requestType": GroupRequestLogType.LEAVE.name,
                                "action": GroupRequestLogActionType.ACCEPT.name,
                                "requestor": {
                                    "id": str(self.user2.id),
                                }
                            },
                            {
                                "requestType": GroupRequestLogType.REMOVED.name,
                                "action": None,
                                "requestor": {
                                    "id": str(self.user2.id),
                                }
                            },
                        ]
                    }
                }
            }
        )

    def test_group_membership_audit_permission_denied(self):
        self.client.force_login(self.user2)

        response = self.query(
            '''
            query($groupId: Int!) {
                groupmanagementGroupMembershipAudit(groupId: $groupId) {
                    group {
                        id
                    }
                    entries {
                        requestType
                        action
                        requestor {
                            id
                        }
                    }
                }
            }
            ''',
            variables={
                "groupId": self.group1.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroupMembershipAudit": None
                },
                "errors": [
                    {
                        "message": 'An unknown error occurred.',
                        "locations": [
                            {
                                "line": 3,
                                "column": 17
                            }
                        ],
                        "path": [
                            "groupmanagementGroupMembershipAudit"
                        ]
                    }
                ]
            }
        )

    def test_group_membership_audit_not_found(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($groupId: Int!) {
                groupmanagementGroupMembershipAudit(groupId: $groupId) {
                    group {
                        id
                    }
                    entries {
                        requestType
                        action
                        requestor {
                            id
                        }
                    }
                }
            }
            ''',
            variables={
                "groupId": generate_invalid_pk(Group),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementGroupMembershipAudit": None
                },
                "errors": [
                    {
                        "message": "Group does not exist",
                        "locations": [
                            {
                                "line": 3,
                                "column": 17
                            }
                        ],
                        "path": [
                            "groupmanagementGroupMembershipAudit"
                        ]
                    }
                ]
            }
        )


class TestAddGroupRequestMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.group = Group.objects.create(name="Test Group 1")

        cls.authgroup = cls.group.authgroup

        cls.authgroup.internal = False
        cls.authgroup.open = False
        cls.authgroup.hidden = False
        cls.authgroup.public = True
        cls.authgroup.save()

        cls.authgroup.states.add(cls.user.profile.state)

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementJoinGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementJoinGroupRequest": {
                        "ok": True,
                        "status": GroupRequestAddStatus.APPLIED.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 1)

    def test_ok_open(self):
        self.client.force_login(self.user)

        self.authgroup.open = True
        self.authgroup.save()

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementJoinGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementJoinGroupRequest": {
                        "ok": True,
                        "status": GroupRequestAddStatus.JOINED.name,
                    }
                }
            }
        )

        self.assertIn(self.group, self.user.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)

    def test_not_joinable(self):
        self.client.force_login(self.user)

        self.authgroup.states.clear()
        self.authgroup.internal = True
        self.authgroup.save()

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementJoinGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementJoinGroupRequest": {
                        "ok": False,
                        "status": GroupRequestAddStatus.CANNOT_JOIN.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_already_in_group(self):
        self.client.force_login(self.user)

        self.user.groups.add(self.group)

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementJoinGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementJoinGroupRequest": {
                        "ok": False,
                        "status": GroupRequestAddStatus.ALREADY_MEMBER.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_group_not_public_and_no_perms(self):
        self.client.force_login(self.user)

        self.authgroup.public = False
        self.authgroup.save()

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementJoinGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementJoinGroupRequest": {
                        "ok": False,
                        "status": GroupRequestAddStatus.CANNOT_JOIN.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_already_applied(self):
        self.client.force_login(self.user)

        GroupRequest.objects.create(
            group=self.group,
            user=self.user,
        )

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementJoinGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementJoinGroupRequest": {
                        "ok": False,
                        "status": GroupRequestAddStatus.ALREADY_APPLIED.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 1)


class TestLeaveGroupRequestMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.group = Group.objects.create(name="Test Group 1")

        cls.authgroup = cls.group.authgroup

        cls.authgroup.internal = False
        cls.authgroup.open = False
        cls.authgroup.hidden = False
        cls.authgroup.public = True
        cls.authgroup.save()

        cls.user.groups.add(cls.group)

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementLeaveGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementLeaveGroupRequest": {
                        "ok": True,
                        "status": GroupRequestLeaveStatus.CREATED_LEAVE_REQUEST.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 1)

    def test_ok_open(self):
        self.client.force_login(self.user)

        self.authgroup.open = True
        self.authgroup.save()

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementLeaveGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementLeaveGroupRequest": {
                        "ok": True,
                        "status": GroupRequestLeaveStatus.LEFT.name,
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)

    def test_internal(self):
        self.client.force_login(self.user)

        self.authgroup.internal = True
        self.authgroup.save()

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementLeaveGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementLeaveGroupRequest": {
                        "ok": False,
                        "status": GroupRequestLeaveStatus.CANNOT_LEAVE.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_not_in_group(self):
        self.client.force_login(self.user)

        self.user.groups.remove(self.group)

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementLeaveGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementLeaveGroupRequest": {
                        "ok": False,
                        "status": GroupRequestLeaveStatus.NOT_MEMBER.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_already_applied(self):
        self.client.force_login(self.user)

        GroupRequest.objects.create(
            group=self.group,
            user=self.user,
        )

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementLeaveGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementLeaveGroupRequest": {
                        "ok": False,
                        "status": GroupRequestLeaveStatus.PENDING_LEAVE_REQUEST.name,
                    }
                }
            }
        )

        self.assertEqual(GroupRequest.objects.count(), 1)

    @override_settings(GROUPMANAGEMENT_AUTO_LEAVE=True)
    def test_auto_leave(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupId: Int!) {
                groupmanagementLeaveGroupRequest(groupId: $groupId) {
                    ok
                    status
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementLeaveGroupRequest": {
                        "ok": True,
                        "status": GroupRequestLeaveStatus.LEFT.name,
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)


class TestGroupMembershipRemove(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()

        cls.group = Group.objects.create(name="Test Group 1")

        cls.authgroup = cls.group.authgroup

        cls.authgroup.internal = False
        cls.authgroup.open = False
        cls.authgroup.hidden = False
        cls.authgroup.public = True
        cls.authgroup.save()

        cls.user2.groups.add(cls.group)

        cls.authgroup.group_leaders.add(cls.user)

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupId: Int!, $userId: Int!) {
                groupmanagementRemoveMember(groupId: $groupId, userId: $userId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
                "userId": self.user2.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRemoveMember": {
                        "ok": True,
                        "error": None,
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)

    def test_cannot_manage(self):
        self.client.force_login(self.user2)

        group2 = Group.objects.create(name="Test Group 2")
        group2.authgroup.group_leaders.add(self.user2)

        response = self.query(
            '''
            mutation($groupId: Int!, $userId: Int!) {
                groupmanagementRemoveMember(groupId: $groupId, userId: $userId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
                "userId": self.user2.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRemoveMember": {
                        "ok": False,
                        "error": 'Permission denied',
                    }
                }
            }
        )

        self.assertIn(self.group, self.user2.groups.all())

    def test_not_in_group(self):
        self.client.force_login(self.user)

        self.user2.groups.remove(self.group)

        response = self.query(
            '''
            mutation($groupId: Int!, $userId: Int!) {
                groupmanagementRemoveMember(groupId: $groupId, userId: $userId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupId": self.group.id,
                "userId": self.user2.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRemoveMember": {
                        "ok": False,
                        "error": "User does not exist in that group",
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user2.groups.all())

    def test_group_not_exists(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupId: Int!, $userId: Int!) {
                groupmanagementRemoveMember(groupId: $groupId, userId: $userId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupId": generate_invalid_pk(Group),
                "userId": self.user2.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRemoveMember": {
                        "ok": False,
                        "error": "Group does not exist",
                    }
                }
            }
        )


class TestGroupMembershipAcceptAndRejectRequestMutations(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()

        cls.group = Group.objects.create(name="Test Group 1")

        cls.authgroup = cls.group.authgroup

        cls.authgroup.internal = False
        cls.authgroup.open = False
        cls.authgroup.hidden = False
        cls.authgroup.public = True
        cls.authgroup.save()

        cls.authgroup.group_leaders.add(cls.user)

        cls.request = GroupRequest.objects.create(
            group=cls.group,
            user=cls.user2,
            leave_request=False,
        )

    def test_accept_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptJoinRequest": {
                        "ok": True,
                        "error": None,
                    }
                }
            }
        )

        self.assertIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)

    def test_accept_request_not_exists(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": generate_invalid_pk(GroupRequest),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptJoinRequest": {
                        "ok": False,
                        "error": "Group request doesn't exist",
                    }
                }
            }
        )

    def test_accept_cannot_manage(self):
        self.client.force_login(self.user2)

        group2 = Group.objects.create(name="Test Group 2")
        group2.authgroup.group_leaders.add(self.user2)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptJoinRequest": {
                        "ok": False,
                        "error": 'Permission denied',
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 0)
        self.assertEqual(GroupRequest.objects.count(), 1)

    @patch.object(GroupRequest, 'delete')
    def test_accept_random_error(self, mock_delete):
        self.client.force_login(self.user)

        mock_delete.side_effect = Exception("Test")

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptJoinRequest": {
                        "ok": False,
                        "error": f'An unhandled error occurred while processing the application from {self.request.main_char} to {self.request.group}.',
                    }
                }
            }
        )

        # Some of these asserts will fail due to delete being after adding group and log
        # I'll push a MR to AA adding a database transaction in the future

        # self.assertNotIn(self.group, self.user2.groups.all())
        # self.assertEqual(RequestLog.objects.count(), 0)
        # self.assertEqual(GroupRequest.objects.count(), 1)

    def test_reject_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectJoinRequest": {
                        "ok": True,
                        "error": None,
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)
        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_reject_request_not_exists(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": generate_invalid_pk(GroupRequest),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectJoinRequest": {
                        "ok": False,
                        "error": "Group request doesn't exist",
                    }
                }
            }
        )

    def test_reject_cannot_manage(self):
        self.client.force_login(self.user2)

        group2 = Group.objects.create(name="Test Group 2")
        group2.authgroup.group_leaders.add(self.user2)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectJoinRequest": {
                        "ok": False,
                        "error": 'Permission denied',
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 0)
        self.assertEqual(GroupRequest.objects.count(), 1)

    @patch.object(GroupRequest, 'delete')
    def test_reject_random_error(self, mock_delete):
        self.client.force_login(self.user)

        mock_delete.side_effect = Exception("Test")

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectJoinRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectJoinRequest": {
                        "ok": False,
                        "error": f'An unhandled error occurred while processing the application from {self.request.main_char} to {self.request.group}.',
                    }
                }
            }
        )

        # Same as test_accept_random_error

        # self.assertNotIn(self.group, self.user2.groups.all())
        # self.assertEqual(RequestLog.objects.count(), 0)
        # self.assertEqual(GroupRequest.objects.count(), 1)


class TestGroupLeaveAcceptAndRejectRequestMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()

        cls.group = Group.objects.create(name="Test Group 1")

        cls.authgroup = cls.group.authgroup

        cls.authgroup.internal = False
        cls.authgroup.open = False
        cls.authgroup.hidden = False
        cls.authgroup.public = True
        cls.authgroup.save()

        cls.authgroup.group_leaders.add(cls.user)

        cls.user2.groups.add(cls.group)

        cls.request = GroupRequest.objects.create(
            group=cls.group,
            user=cls.user2,
            leave_request=True,
        )

    def test_accept_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptLeaveRequest": {
                        "ok": True,
                        "error": None,
                    }
                }
            }
        )

        self.assertNotIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)
        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_accept_request_not_exists(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": generate_invalid_pk(GroupRequest),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptLeaveRequest": {
                        "ok": False,
                        "error": "Group request doesn't exist",
                    }
                }
            }
        )

    def test_accept_cannot_manage(self):
        self.client.force_login(self.user2)

        group2 = Group.objects.create(name="Test Group 2")
        group2.authgroup.group_leaders.add(self.user2)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptLeaveRequest": {
                        "ok": False,
                        "error": 'Permission denied',
                    }
                }
            }
        )

        self.assertIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 0)
        self.assertEqual(GroupRequest.objects.count(), 1)

    @patch.object(GroupRequest, 'delete')
    def test_accept_random_error(self, mock_delete):
        self.client.force_login(self.user)

        mock_delete.side_effect = Exception("Test")

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementAcceptLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementAcceptLeaveRequest": {
                        "ok": False,
                        "error": f'An unhandled error occurred while processing the application from {self.request.main_char} to {self.request.group}.',
                    }
                }
            }
        )

        # Same as test_accept_random_error

        # self.assertIn(self.group, self.user2.groups.all())
        # self.assertEqual(RequestLog.objects.count(), 0)
        # self.assertEqual(GroupRequest.objects.count(), 1)

    def test_reject_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectLeaveRequest": {
                        "ok": True,
                        "error": None,
                    }
                }
            }
        )

        self.assertIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 1)
        self.assertEqual(GroupRequest.objects.count(), 0)

    def test_reject_request_not_exists(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": generate_invalid_pk(GroupRequest),
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectLeaveRequest": {
                        "ok": False,
                        "error": "Group request doesn't exist",
                    }
                }
            }
        )

    def test_reject_cannot_manage(self):
        self.client.force_login(self.user2)

        group2 = Group.objects.create(name="Test Group 2")
        group2.authgroup.group_leaders.add(self.user2)

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectLeaveRequest": {
                        "ok": False,
                        "error": 'Permission denied',
                    }
                }
            }
        )

        self.assertIn(self.group, self.user2.groups.all())
        self.assertEqual(RequestLog.objects.count(), 0)
        self.assertEqual(GroupRequest.objects.count(), 1)

    @patch.object(GroupRequest, 'delete')
    def test_reject_random_error(self, mock_delete):
        self.client.force_login(self.user)

        mock_delete.side_effect = Exception("Test")

        response = self.query(
            '''
            mutation($groupRequestId: Int!) {
                groupmanagementRejectLeaveRequest(groupRequestId: $groupRequestId) {
                    ok
                    error
                }
            }
            ''',
            variables={
                "groupRequestId": self.request.id,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "groupmanagementRejectLeaveRequest": {
                        "ok": False,
                        "error": f'An unhandled error occurred while processing the application from {self.request.main_char} to {self.request.group}.',
                    }
                }
            }
        )

        # Same as test_reject_random_error of other test class

        # self.assertIn(self.group, self.user2.groups.all())
        # self.assertEqual(RequestLog.objects.count(), 0)
        # self.assertEqual(GroupRequest.objects.count(), 1)
