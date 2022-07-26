import graphene
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model

from allianceauth.services.hooks import get_extension_logger

from allianceauth_pve.models import Rotation, EntryCharacter, Entry, EntryRole


logger = get_extension_logger(__name__)

User = get_user_model()


class RattingSummaryType(graphene.ObjectType):
    main_character = graphene.Field('allianceauth_graphql.eveonline.types.EveCharacterType')
    helped_setups = graphene.Int()
    estimated_total = graphene.Float()
    actual_total = graphene.Float()

    def resolve_character(self, info):
        try:
            return User.objects.get(pk=self['user']).profile.main_character
        except:
            return None


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
    summary = graphene.List(RattingSummaryType)

    class Meta:
        model = Rotation

    def resolve_entries(self, info):
        return self.entries.order_by('-created_at')

    def resolve_summary(self, info):
        return self.summary.order_by('-estimated_total')


class EntryRoleType(DjangoObjectType):
    class Meta:
        model = EntryRole
