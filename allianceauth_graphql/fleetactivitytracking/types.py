from graphene_django import DjangoObjectType

from allianceauth.fleetactivitytracking.models import Fatlink, Fat


class FatlinkType(DjangoObjectType):
    class Meta:
        model = Fatlink


class FatType(DjangoObjectType):
    class Meta:
        model = Fat
