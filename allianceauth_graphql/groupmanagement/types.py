import graphene
from graphene_django import DjangoObjectType

from django.contrib.auth.models import User

from allianceauth.groupmanagement.models import GroupRequest, AuthGroup, RequestLog


class AuthGroupType(DjangoObjectType):
    group = graphene.Field('allianceauth_graphql.authentication.types.GroupType', required=True)

    class Meta:
        model = AuthGroup
        fields = ('group', 'description',)


class GroupRequestAddStatus(graphene.Enum):
    CANNOT_JOIN = 1
    ALREADY_MEMBER = 2
    JOINED = 3
    ALREADY_APPLIED = 4
    APPLIED = 5


class GroupRequestLeaveStatus(graphene.Enum):
    CANNOT_LEAVE = 1
    NOT_MEMBER = 2
    LEFT = 3
    PENDING_LEAVE_REQUEST = 4
    CREATED_LEAVE_REQUEST = 5


class GroupRequestType(DjangoObjectType):
    group = graphene.Field('allianceauth_graphql.authentication.types.GroupType', required=True)
    user = graphene.Field('allianceauth_graphql.authentication.types.UserType', required=True)

    class Meta:
        model = GroupRequest


class GroupManagementType(graphene.ObjectType):
    leave_requests = graphene.List(GroupRequestType)
    accept_requests = graphene.List(GroupRequestType)
    auto_leave = graphene.Boolean()


class MemberType(graphene.ObjectType):
    user = graphene.Field('allianceauth_graphql.authentication.types.UserType')
    is_leader = graphene.Boolean()


class GroupMembershipListType(graphene.ObjectType):
    group = graphene.Field('allianceauth_graphql.authentication.types.GroupType')
    members = graphene.List(MemberType)


class GroupRequestLogType(graphene.Enum):
    REMOVED = 1
    LEAVE = 2
    JOIN = 3


class GroupRequestLogActionType(graphene.Enum):
    ACCEPT = 1
    REJECT = 2


class RequestLogType(DjangoObjectType):
    request_type = graphene.Field(GroupRequestLogType)
    requestor = graphene.Field('allianceauth_graphql.authentication.types.UserType')
    action = graphene.Field(GroupRequestLogActionType)
    group = graphene.Field('allianceauth_graphql.authentication.types.GroupType', required=True)

    class Meta:
        model = RequestLog
        fields = ('id', 'group', 'request_actor', 'date',)

    def resolve_request_type(self, info):
        if self.request_type is None:
            return GroupRequestLogType.REMOVED
        elif self.request_type:  # True
            return GroupRequestLogType.LEAVE
        else:  # False
            return GroupRequestLogType.JOIN

    def resolve_action(self, info):
        if self.request_type is None:
            return None
        elif self.action:
            return GroupRequestLogActionType.ACCEPT
        else:
            return GroupRequestLogActionType.REJECT

    def resolve_requestor(self, info):
        username = self.requestor()
        return User.objects.get(username=username)


class GroupMembershipAuditType(graphene.ObjectType):
    group = graphene.Field('allianceauth_graphql.authentication.types.GroupType')
    entries = graphene.List(RequestLogType)
