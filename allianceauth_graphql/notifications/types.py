from graphene_django import DjangoObjectType

from allianceauth.notifications.models import Notification


class NotificationType(DjangoObjectType):
    class Meta:
        model = Notification
