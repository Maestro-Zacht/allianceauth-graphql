import graphene
from graphql_jwt.decorators import login_required

from allianceauth.notifications.models import Notification

from .types import NotificationType


class Query:
    notif_read_list = graphene.List(NotificationType)
    notif_unread_list = graphene.List(NotificationType)
    notif_unread_count = graphene.Int(user_pk=graphene.ID())

    @login_required
    def resolve_notifications_read_list(self, info):
        return Notification.objects.filter(user=info.context.user, viewed=True).order_by("-timestamp")

    @login_required
    def resolve_notifications_unread_list(self, info):
        return Notification.objects.filter(user=info.context.user, viewed=False).order_by("-timestamp")

    def resolve_notif_unread_count(self, info, user_pk=None):
        if user_pk is None and not info.context.user.is_authenticated:
            return -1

        pk = user_pk if user_pk is not None else info.context.user.pk
        return Notification.objects.user_unread_count(pk)
