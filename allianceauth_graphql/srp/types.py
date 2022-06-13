import graphene
from graphene_django import DjangoObjectType

from allianceauth.srp.models import SrpFleetMain, SrpUserRequest


class SrpFleetMainType(DjangoObjectType):
    total_cost = graphene.Int(required=True)
    pending_requests = graphene.Int(required=True)

    class Meta:
        model = SrpFleetMain


class SrpUserRequestType(DjangoObjectType):
    class Meta:
        model = SrpUserRequest
