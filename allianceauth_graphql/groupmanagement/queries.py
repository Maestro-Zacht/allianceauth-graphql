import graphene
from graphql_jwt.decorators import login_required, user_passes_test

from django.db.models import Case, When, Exists, OuterRef, Q, Count
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from allianceauth.groupmanagement.managers import GroupManager
from allianceauth.groupmanagement.models import GroupRequest, RequestLog
from allianceauth.services.hooks import get_extension_logger

from allianceauth_graphql.authentication.types import GroupType

from .types import GroupManagementType, GroupMembershipListType, GroupMembershipAuditType


logger = get_extension_logger(__name__)


class Query:
    user_joinable_groups = graphene.List(GroupType)
    group_management = graphene.Field(GroupManagementType)
    group_membership = graphene.List(GroupType)
    group_membership_list = graphene.Field(GroupMembershipListType, group_id=graphene.Int(required=True))
    group_membership_audit = graphene.Field(GroupMembershipAuditType, group_id=graphene.Int(required=True))

    @login_required
    def resolve_user_joinable_groups(self, info):
        user = info.context.user
        groups_qs = GroupManager.get_joinable_groups_for_user(user, include_hidden=False).order_by('name')

        return groups_qs.annotate(
            status=Case(
                When(
                    Exists(user.groups.filter(pk=OuterRef('pk'))),
                    then=Case(
                        When(
                            Exists(GroupRequest.objects.filter(user=user, group_id=OuterRef('pk'))),
                            then=2
                        ),
                        default=1
                    )
                ),
                When(
                    ~Exists(GroupRequest.objects.filter(user=user, group_id=OuterRef('pk'))),
                    then=Case(
                        When(
                            Q(authgroup__open=True), then=3
                        ),
                        default=4
                    )
                ),
                default=2
            )
        )

    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def resolve_group_management(self, info):
        user = info.context.user
        logger.debug("group_management called by user %s" % user)
        acceptrequests = []
        leaverequests = []

        base_group_query = GroupRequest.objects.select_related('user', 'group', 'user__profile__main_character')

        if GroupManager.has_management_permission(user):
            # Full access
            group_requests = base_group_query.all()
        else:
            # Group specific leader
            users__groups = GroupManager.get_group_leaders_groups(user)
            group_requests = base_group_query.filter(group__in=users__groups)

        for grouprequest in group_requests:
            if grouprequest.leave_request:
                leaverequests.append(grouprequest)
            else:
                acceptrequests.append(grouprequest)

        logger.debug(f"Providing user {user} with {len(acceptrequests)} acceptrequests and {len(leaverequests)} leaverequests.")

        return {
            'leave_requests': leaverequests,
            'accept_requests': acceptrequests,
            'auto_leave': getattr(settings, 'GROUPMANAGEMENT_AUTO_LEAVE', False),
        }

    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def resolve_group_membership(self, info):
        user = info.context.user
        logger.debug("group_membership called by user %s" % user)
        # Get all open and closed groups
        if GroupManager.has_management_permission(user):
            # Full access
            groups = GroupManager.get_all_non_internal_groups()
        else:
            # Group leader specific
            groups = GroupManager.get_group_leaders_groups(user)

        return groups.exclude(authgroup__internal=True).annotate(num_members=Count('user')).order_by('name')

    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def resolve_group_membership_list(self, info, group_id):
        user = info.context.user
        logger.debug(f"group_membership_list called by user {user} for group id {group_id}")
        try:
            group = Group.objects.get(id=group_id)
            # Check its a joinable group i.e. not corp or internal
            # And the user has permission to manage it
            if (not GroupManager.check_internal_group(group)
                    or not GroupManager.can_manage_group(user, group)
                    ):
                logger.warning(
                    "User %s attempted to view the membership of group %s "
                    "but permission was denied" % (user, group_id)
                )
                raise PermissionDenied

        except ObjectDoesNotExist:
            raise Exception("Group doesn't exist")

        group_leaders = group.authgroup.group_leaders.all()
        members = list()
        for member in \
            group.user_set\
                .all()\
                .order_by('profile__main_character__character_name'):

            members.append({
                'user': member,
                'is_leader': member in group_leaders
            })

        return {'group': group, 'members': members}

    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def resolve_group_membership_audit(self, info, group_id):
        user = info.context.user
        logger.debug("group_management_audit called by user %s" % user)
        try:
            group = Group.objects.get(id=group_id)
            # Check its a joinable group i.e. not corp or internal
            # And the user has permission to manage it
            if not GroupManager.check_internal_group(group) or not GroupManager.can_manage_group(user, group):
                logger.warning(f"User {user} attempted to view the membership of group {group_id} but permission was denied")
                raise PermissionDenied

        except ObjectDoesNotExist:
            raise Exception("Group does not exist")

        entries = RequestLog.objects.filter(group=group).order_by('-date')

        return {'group': group.name, 'entries': entries}
