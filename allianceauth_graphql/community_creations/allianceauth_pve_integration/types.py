import graphene
from graphene_django import DjangoObjectType

from allianceauth_pve.models import Rotation, EntryCharacter, Entry


class EntryCharacterType(DjangoObjectType):
    class Meta:
        model = EntryCharacter


class EntryType(DjangoObjectType):
    estimated_total_after_tax = graphene.Float()
    total_shares_count = graphene.Int()

    class Meta:
        model = Entry


class RotationType(DjangoObjectType):
    sales_percentage = graphene.Float()
    days_since = graphene.Int()
    estimated_total = graphene.Float()

    class Meta:
        model = Rotation

    def resolve_entries(self, info):
        return self.entries.order_by('-created_at')

    def resolve_summary(self, info):
        return self.summary.order_by('-estimated_total')
