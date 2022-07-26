import graphene
from graphql_jwt.decorators import login_required

from allianceauth.notifications.models import Notification

from .types import NotificationType


class MarkNotifReadMutation(graphene.Mutation):
    class Arguments:
        notif_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    notification = graphene.Field(NotificationType)

    @classmethod
    @login_required
    def mutate(cls, root, info, notif_id):
        notif = Notification.objects.get(pk=notif_id)
        if notif.user == info.context.user:
            notif.mark_viewed()
            ok = True
        else:
            ok = False

        return cls(ok=ok, notification=notif if ok else None)


class DeleteNotificationMutation(graphene.Mutation):
    class Arguments:
        notif_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    def mutate(cls, root, info, notif_id):
        notif = Notification.objects.get(pk=notif_id)

        if notif.user == info.context.user:
            notif.delete()
            ok = True
        else:
            ok = False

        return cls(ok=ok)


class AllReadMutation(graphene.Mutation):

    ok = graphene.Boolean()

    @classmethod
    @login_required
    def mutate(cls, root, info):
        Notification.objects.filter(user=info.context.user).update(viewed=True)
        return cls(ok=True)


class DeleteAllReadMutation(graphene.Mutation):

    ok = graphene.Boolean()

    @classmethod
    @login_required
    def mutate(cls, root, info):
        Notification.objects.filter(user=info.context.user, viewed=True).delete()
        return cls(ok=True)


class Mutation:
    notif_mark_as_read = MarkNotifReadMutation.Field()
    notif_delete = DeleteNotificationMutation.Field()
    notif_mark_all_read = AllReadMutation.Field()
