import graphene
from graphene_django import DjangoObjectType

from esi.models import Token, Scope

from allianceauth.eveonline.models import EveCharacter


class ScopeType(DjangoObjectType):
    friendly_name = graphene.String(required=True)

    class Meta:
        model = Scope
        fields = ('name', 'help_text',)


class TokenType(DjangoObjectType):
    character = graphene.Field('allianceauth_graphql.eveonline.types.EveCharacterType')

    class Meta:
        model = Token
        fields = ('id', 'user', 'scopes',)

    def resolve_character(self, info):
        return EveCharacter.objects.get(character_id=self.character_id)
