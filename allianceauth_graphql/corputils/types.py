import graphene
from graphene_django import DjangoObjectType

from django.contrib.auth import get_user_model

from allianceauth.corputils.models import CorpStats
from allianceauth.eveonline.models import EveCharacter


User = get_user_model()


class CorpStatsType(DjangoObjectType):
    members = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')
    registered = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')
    unregistered = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')
    mains = graphene.List('allianceauth_graphql.eveonline.types.EveCharacterType')

    class Meta:
        model = CorpStats
        fields = ('corp', 'last_update',)

    def resolve_members(self, info):
        return EveCharacter.objects.filter(character_id__in=self.members.values('character_id'))\
            .select_related('character_ownership', 'character_ownership__user__profile__main_character')\
            .prefetch_related('character_ownership__user__character_ownerships')\
            .prefetch_related('character_ownership__user__character_ownerships__character')

    def resolve_registered(self, info):
        return EveCharacter.objects.filter(character_id__in=self.members.values('character_id'), character_ownership__isnull=False)\
            .select_related('character_ownership', 'character_ownership__user__profile__main_character')\
            .prefetch_related('character_ownership__user__character_ownerships')\
            .prefetch_related('character_ownership__user__character_ownerships__character')

    def resolve_unregistered(self, info):
        return EveCharacter.objects.filter(character_id__in=self.members.values('character_id'), character_ownership__isnull=True)

    def resolve_mains(self, info):
        main_ids = User.objects.values('profile__main_character__character_id')
        return EveCharacter.objects.filter(character_id__in=self.members.values('character_id'), character_id__in=main_ids)
