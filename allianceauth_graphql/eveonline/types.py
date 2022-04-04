import graphene
from graphene_django import DjangoObjectType
from allianceauth.eveonline.models import EveCharacter, EveFactionInfo, EveAllianceInfo, EveCorporationInfo


class EveFactionInfoType(DjangoObjectType):
    class Meta:
        model = EveFactionInfo


class EveAllianceInfoType(DjangoObjectType):
    class Meta:
        model = EveAllianceInfo


class EveCorporationInfoType(DjangoObjectType):
    class Meta:
        model = EveCorporationInfo


class EveCharacterType(DjangoObjectType):
    is_biomassed = graphene.Boolean(required=True)
    alliance = graphene.Field(EveAllianceInfoType)
    corporation = graphene.Field(EveCorporationInfoType, required=True)
    faction = graphene.Field(EveFactionInfoType)

    class Meta:
        model = EveCharacter
