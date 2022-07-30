import graphene
from graphql_jwt.decorators import login_required, user_passes_test

from django.contrib.auth.models import Group
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from allianceauth.groupmanagement.managers import GroupManager
from allianceauth.groupmanagement.models import RequestLog, GroupRequest
from allianceauth.services.hooks import get_extension_logger
from allianceauth.notifications import notify

from .types import GroupRequestAddStatus, GroupRequestLeaveStatus


logger = get_extension_logger(__name__)


class AddGroupRequest(graphene.Mutation):
    class Arguments:
        group_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    status = graphene.Field(GroupRequestAddStatus)

    @classmethod
    @login_required
    def mutate(cls, root, info, group_id):
        user = info.context.user
        group = Group.objects.get(id=group_id)

        logger.debug(f"group_request_add called by user {user} for group id {group_id}")

        if not GroupManager.joinable_group(group, user.profile.state):
            logger.warning(f"User {user} attempted to join group id {group_id} but it is not a joinable group")
            status = GroupRequestAddStatus.CANNOT_JOIN
            ok = False
        elif group in user.groups.all():
            logger.warning(f"User {user} attempted to join group id {group_id} but they are already a member.")
            status = GroupRequestAddStatus.ALREADY_MEMBER
            ok = False
        elif not user.has_perm('groupmanagement.request_groups') and not group.authgroup.public:
            logger.warning(f"User {user} attempted to join group id {group_id} but it is not a public group")
            status = GroupRequestAddStatus.CANNOT_JOIN
            ok = False
        elif group.authgroup.open:
            logger.info(f"{user} joining {group} as is an open group")
            user.groups.add(group)
            request_info = user.username + ":" + group.name
            log = RequestLog(request_type=False, group=group, request_info=request_info, action=1, request_actor=user)
            log.save()

            status = GroupRequestAddStatus.JOINED
            ok = True
        elif GroupRequest.objects.filter(user=user, group=group).exists():
            logger.info(f"{user} attempted to join {group} but already has an open application")
            status = GroupRequestAddStatus.ALREADY_MEMBER
            ok = False
        else:
            grouprequest = GroupRequest()
            grouprequest.group = group
            grouprequest.user = user
            grouprequest.leave_request = False
            grouprequest.save()
            logger.info(f"Created group request for user {user} to group {group}")
            grouprequest.notify_leaders()

            status = GroupRequestAddStatus.APPLIED
            ok = True

        return cls(ok=ok, status=status)


class LeaveGroupRequest(graphene.Mutation):
    class Arguments:
        group_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    status = graphene.Field(GroupRequestLeaveStatus)

    @classmethod
    @login_required
    def mutate(cls, root, info, group_id):
        user = info.context.user
        logger.debug(f"group_request_leave called by user {user} for group id {group_id}")
        group = Group.objects.get(id=group_id)

        if not GroupManager.check_internal_group(group):
            logger.warning(f"User {user} attempted to leave group id {group_id} but it is not a joinable group")
            status = GroupRequestLeaveStatus.CANNOT_LEAVE
            ok = False
        elif group not in user.groups.all():
            logger.debug(f"User {user} attempted to leave group id {group_id} but they are not a member")
            status = GroupRequestLeaveStatus.NOT_MEMBER
            ok = False
        elif group.authgroup.open:
            logger.info(f"{user} leaving {group} as is an open group")
            request_info = user.username + ":" + group.name
            log = RequestLog(request_type=True, group=group, request_info=request_info, action=1, request_actor=user)
            log.save()
            user.groups.remove(group)

            status = GroupRequestLeaveStatus.LEFT
            ok = True
        elif GroupRequest.objects.filter(user=user, group=group):
            logger.info(f"{user} attempted to leave {group} but already has an pending leave request.")
            status = GroupRequestLeaveStatus.PENDING_LEAVE_REQUEST
            ok = False
        elif getattr(settings, 'GROUPMANAGEMENT_AUTO_LEAVE', False):
            logger.info(f"{user} leaving joinable group {group} due to auto_leave")
            request_info = user.username + ":" + group.name
            log = RequestLog(request_type=True, group=group, request_info=request_info, action=1, request_actor=user)
            log.save()
            user.groups.remove(group)
        else:
            grouprequest = GroupRequest()
            grouprequest.group = group
            grouprequest.user = user
            grouprequest.leave_request = True
            grouprequest.save()
            logger.info(f"Created group leave request for user {user} to group {group}")
            grouprequest.notify_leaders()

            status = GroupRequestLeaveStatus.CREATED_LEAVE_REQUEST
            ok = True

        return cls(ok=ok, status=status)


class GroupMembershipRemove(graphene.Mutation):
    class Arguments:
        group_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def mutate(cls, root, info, group_id, user_id):
        ok = False
        error = None
        a_user = info.context.user
        logger.debug(f"group_membership_remove called by user {a_user} for group id {group_id} on user id {user_id}")
        try:
            group = Group.objects.get(pk=group_id)
            # Check its a joinable group i.e. not corp or internal
            # And the user has permission to manage it
            if not GroupManager.check_internal_group(group) or not GroupManager.can_manage_group(a_user, group):
                logger.warning(f"User {a_user} attempted to remove a user from group {group_id} but permission was denied")
                error = 'Permission denied'
            else:
                try:
                    user = group.user_set.get(id=user_id)
                    request_info = user.username + ":" + group.name
                    log = RequestLog(request_type=None, group=group, request_info=request_info, action=1, request_actor=a_user)
                    log.save()
                    # Remove group from user
                    user.groups.remove(group)
                    logger.info(f"User {a_user} removed user {user} from group {group}")
                    ok = True
                except ObjectDoesNotExist:
                    error = "User does not exist in that group"

        except ObjectDoesNotExist:
            error = "Group does not exist"

        return cls(ok=ok, error=error)


class GroupMembershipAcceptRequest(graphene.Mutation):
    class Arguments:
        group_request_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def mutate(cls, root, info, group_request_id):
        user = info.context.user
        ok = True
        error = None
        logger.debug(f"group_accept_request called by user {user} for grouprequest id {group_request_id}")
        try:
            group_request = GroupRequest.objects.get(id=group_request_id)
        except GroupRequest.DoesNotExist:
            error = "Group request doesn't exist"
            ok = False
        else:
            try:
                group, created = Group.objects.get_or_create(name=group_request.group.name)

                if not GroupManager.joinable_group(group_request.group, group_request.user.profile.state) or \
                        not GroupManager.can_manage_group(user, group_request.group):
                    error = "Permission denied"
                    ok = False
                else:
                    group_request.user.groups.add(group)
                    group_request.user.save()
                    log = RequestLog(request_type=group_request.leave_request, group=group, request_info=group_request.__str__(), action=1, request_actor=user)
                    log.save()
                    group_request.delete()
                    logger.info("User {} accepted group request from user {} to group {}".format(
                        user, group_request.user, group_request.group.name))
                    notify(group_request.user, "Group Application Accepted", level="success",
                           message="Your application to %s has been accepted." % group_request.group)
            except PermissionDenied as p:
                logger.warning(f"User {user} attempted to accept group join request {group_request_id} but permission was denied")
                error = "Permission denied"
                ok = False
            except:
                error = 'An unhandled error occurred while processing the application from %(mainchar)s to %(group)s.' % {"mainchar": group_request.main_char, "group": group_request.group}
                logger.exception("Unhandled exception occurred while user {} attempting to accept grouprequest id {}.".format(user, group_request_id))
                ok = False

        return cls(ok=ok, error=error)


class GroupMembershipRejectRequest(graphene.Mutation):
    class Arguments:
        group_request_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def mutate(cls, root, info, group_request_id):
        user = info.context.user
        ok = True
        error = None

        logger.debug(f"group_reject_request called by user {user} for group request id {group_request_id}")
        try:
            group_request = GroupRequest.objects.get(id=group_request_id)
        except GroupRequest.DoesNotExist:
            error = "Group request doesn't exist"
            ok = False
        else:
            try:
                if not GroupManager.can_manage_group(user, group_request.group):
                    error = "Permission denied"
                    ok = False
                else:
                    logger.info("User {} rejected group request from user {} to group {}".format(
                        user, group_request.user, group_request.group.name))
                    log = RequestLog(request_type=group_request.leave_request, group=group_request.group, request_info=group_request.__str__(), action=0, request_actor=user)
                    log.save()
                    group_request.delete()
                    notify(group_request.user, "Group Application Rejected", level="danger", message="Your application to %s has been rejected." % group_request.group)

            except PermissionDenied as p:
                logger.warning(f"User {user} attempted to reject group join request {group_request_id} but permission was denied")
                error = "Permission denied"
                ok = False
            except:
                error = 'An unhandled error occurred while processing the application from %(mainchar)s to %(group)s.' % {"mainchar": group_request.main_char, "group": group_request.group}
                logger.exception("Unhandled exception occurred while user {} attempting to accept grouprequest id {}.".format(user, group_request_id))
                ok = False

        return cls(ok=ok, error=error)


class GroupLeaveAcceptRequest(graphene.Mutation):
    class Arguments:
        group_request_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def mutate(cls, root, info, group_request_id):
        user = info.context.user
        ok = True
        error = None
        logger.debug(
            f"group_leave_accept_request called by user {user} for group request id {group_request_id}")
        try:
            group_request = GroupRequest.objects.get(id=group_request_id)
        except GroupRequest.DoesNotExist:
            error = "Group request doesn't exist"
            ok = False
        else:
            try:
                if not GroupManager.can_manage_group(user, group_request.group):
                    error = "Permission denied"
                    ok = False
                else:
                    group, created = Group.objects.get_or_create(name=group_request.group.name)
                    group_request.user.groups.remove(group)
                    group_request.user.save()
                    log = RequestLog(request_type=group_request.leave_request, group=group_request.group, request_info=group_request.__str__(), action=1, request_actor=user)
                    log.save()
                    group_request.delete()
                    logger.info("User {} accepted group leave request from user {} to group {}".format(
                        user, group_request.user, group_request.group.name))
                    notify(group_request.user, "Group Leave Request Accepted", level="success",
                           message="Your request to leave %s has been accepted." % group_request.group)
            except PermissionDenied as p:
                logger.warning(f"User {user} attempted to accept group leave request {group_request_id} but permission was denied")
                error = "Permission denied"
                ok = False
            except:
                error = 'An unhandled error occurred while processing the application from %(mainchar)s to %(group)s.' % {"mainchar": group_request.main_char, "group": group_request.group}
                logger.exception("Unhandled exception occurred while user {} attempting to accept grouprequest id {}.".format(user, group_request_id))
                ok = False

        return cls(ok=ok, error=error)


class GroupLeaveRejectRequest(graphene.Mutation):
    class Arguments:
        group_request_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @user_passes_test(GroupManager.can_manage_groups)
    def mutate(cls, root, info, group_request_id):
        user = info.context.user
        ok = True
        error = None

        logger.debug(
            f"group_leave_reject_request called by user {user} for group request id {group_request_id}")
        try:
            group_request = GroupRequest.objects.get(id=group_request_id)
        except GroupRequest.DoesNotExist:
            error = "Group request doesn't exist"
            ok = False
        else:
            try:
                if not GroupManager.can_manage_group(user, group_request.group):
                    error = "Permission denied"
                    ok = False
                else:
                    log = RequestLog(request_type=group_request.leave_request, group=group_request.group, request_info=group_request.__str__(), action=0, request_actor=user)
                    log.save()
                    group_request.delete()
                    logger.info("User {} rejected group leave request from user {} for group {}".format(
                        user, group_request.user, group_request.group.name))
                    notify(group_request.user, "Group Leave Request Rejected", level="danger", message="Your request to leave %s has been rejected." % group_request.group)
            except PermissionDenied as p:
                logger.warning(f"User {user} attempted to reject group leave request {group_request_id} but permission was denied")
                error = "Permission denied"
                ok = False
            except:
                error = 'An unhandled error occurred while processing the application from %(mainchar)s to %(group)s.' % {"mainchar": group_request.main_char, "group": group_request.group}
                logger.exception("Unhandled exception occurred while user {} attempting to accept grouprequest id {}.".format(user, group_request_id))
                ok = False

        return cls(ok=ok, error=error)


class Mutation:
    add_group_request = AddGroupRequest.Field()
    leave_group_request = LeaveGroupRequest.Field()
    group_membership_remove = GroupMembershipRemove.Field()
    group_membership_accept_request = GroupMembershipAcceptRequest.Field()
    group_membership_reject_request = GroupMembershipRejectRequest.Field()
    group_leave_accept_request = GroupLeaveAcceptRequest.Field()
