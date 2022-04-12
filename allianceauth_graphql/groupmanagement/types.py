from django.contrib.auth.models import Group

import graphene
from graphene_django import DjangoObjectType

from allianceauth.groupmanagement.models import AuthGroup


class ApplicationEnum(graphene.Enum):
    JOINED = 1
    PENDING = 2
    CAN_JOIN = 3
    CAN_APPLY = 4


class AuthGroupType(DjangoObjectType):
    application = graphene.Field(ApplicationEnum)

    class Meta:
        model = AuthGroup
        fields = ('group', 'description',)
