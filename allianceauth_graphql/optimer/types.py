from graphene_django import DjangoObjectType

from allianceauth.optimer.models import OpTimer, OpTimerType


class OpTimerModelType(DjangoObjectType):
    class Meta:
        model = OpTimer


class OpTimerTypeType(DjangoObjectType):
    class Meta:
        model = OpTimerType
