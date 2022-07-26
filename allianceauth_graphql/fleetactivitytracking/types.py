import graphene
from graphene_django import DjangoObjectType

from allianceauth.fleetactivitytracking.models import Fatlink, Fat


class FatlinkType(DjangoObjectType):
    class Meta:
        model = Fatlink


class FatType(DjangoObjectType):
    class Meta:
        model = Fat


class FatUserStatsType(graphene.ObjectType):
    user = graphene.Field('allianceauth_graphql.authentication.types.UserType', required=True)
    num_chars = graphene.Int(required=True)
    num_fats = graphene.Int(required=True)
    average_fats = graphene.Float(required=True)


class FatCorpStatsType(graphene.ObjectType):
    corporation = graphene.Field('allianceauth_graphql.eveonline.types.EveCorporationInfoType', required=True)
    num_fats = graphene.Int(required=True)
    avg_fats = graphene.Float(required=True)


class FatPersonalStatsType(graphene.ObjectType):
    month = graphene.Int(required=True)
    year = graphene.Int(required=True)
    num_fats = graphene.Int(required=True)


class FatCollectedLinkType(graphene.ObjectType):
    shiptype = graphene.String(required=True)
    times_used = graphene.Int(required=True)


class FatPersonalMonthlyStatsType(graphene.ObjectType):
    collected_links = graphene.List(FatCollectedLinkType, required=True)
    created_links = graphene.List(FatlinkType, required=True)
