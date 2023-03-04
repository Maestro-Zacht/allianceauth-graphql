import graphene
from graphene_django import DjangoObjectType

from allianceauth.eveonline.models import EveCharacter, EveFactionInfo, EveAllianceInfo, EveCorporationInfo


class EveFactionInfoType(DjangoObjectType):
    class Meta:
        model = EveFactionInfo
        fields = ('id', 'faction_id', 'faction_name', )


class EveAllianceInfoType(DjangoObjectType):
    class Meta:
        model = EveAllianceInfo
        fields = ('id', 'alliance_id', 'alliance_name', 'alliance_ticker', 'executor_corp_id', 'evecorporationinfo_set', )


class EveCorporationInfoType(DjangoObjectType):
    logo_url_32 = graphene.String(required=True)
    logo_url_64 = graphene.String(required=True)
    logo_url_128 = graphene.String(required=True)
    logo_url_256 = graphene.String(required=True)

    class Meta:
        model = EveCorporationInfo
        fields = ('id', 'corporation_id', 'corporation_name', 'corporation_ticker', 'alliance', 'ceo_id', 'member_count', )


class EveCharacterType(DjangoObjectType):
    is_biomassed = graphene.Boolean(required=True)
    alliance = graphene.Field(EveAllianceInfoType)
    corporation = graphene.Field(EveCorporationInfoType, required=True)
    faction = graphene.Field(EveFactionInfoType)

    zkillboard = graphene.String(required=True)

    class Meta:
        model = EveCharacter
        fields = ('id', 'character_name', 'character_id', 'corporation_id', 'corporation_name', 'alliance_id', 'alliance_name', 'faction_id', 'faction_name', )

    def resolve_zkillboard(self, info):
        return f"https://zkillboard.com/character/{self.character_id}/"
