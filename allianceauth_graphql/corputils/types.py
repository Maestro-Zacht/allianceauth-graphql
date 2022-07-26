import graphene
from graphene_django import DjangoObjectType

from django.contrib.auth import get_user_model
from django.db.models import Q

from allianceauth.corputils.models import CorpStats, CorpMember
from allianceauth.eveonline.models import EveCharacter


User = get_user_model()


class CorpMemberType(DjangoObjectType):
    character = graphene.Field('allianceauth_graphql.eveonline.types.EveCharacterType')

    class Meta:
        model = CorpMember
        fields = ('corpstats', 'character_id', 'character_name',)

    def resolve_character(self, info):
        try:
            return EveCharacter.objects.get(character_id=self.character_id)
        except EveCharacter.DoesNotExist:
            return None


class CorpStatsType(DjangoObjectType):
    registered = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')
    unregistered = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')
    mains = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')

    class Meta:
        model = CorpStats
        fields = ('corp', 'last_update', 'members',)

    def resolve_registered(self, info):
        return EveCharacter.objects.filter(character_id__in=self.members.values('character_id'), character_ownership__isnull=False)\
            .select_related('character_ownership', 'character_ownership__user__profile__main_character')\
            .prefetch_related('character_ownership__user__character_ownerships')\
            .prefetch_related('character_ownership__user__character_ownerships__character')

    def resolve_unregistered(self, info):
        return EveCharacter.objects.filter(character_id__in=self.members.values('character_id'), character_ownership__isnull=True)

    def resolve_mains(self, info):
        main_ids = User.objects.values('profile__main_character__character_id')
        return EveCharacter.objects.filter(Q(character_id__in=self.members.values('character_id')) & Q(character_id__in=main_ids))
