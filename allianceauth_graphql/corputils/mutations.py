import graphene
from graphql_jwt.decorators import login_required, user_passes_test, permission_required

from allianceauth.corputils.views import access_corpstats_test, SWAGGER_SPEC_PATH
from allianceauth.corputils.models import CorpStats
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo

from ..decorators import tokens_required

from esi.models import Token


class AddCorpStatsMutation(graphene.Mutation):
    class Arguments:
        token_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @user_passes_test(access_corpstats_test)
    @permission_required('corputils.add_corpstats')
    @tokens_required(scopes='esi-corporations.read_corporation_membership.v1')
    def mutate(cls, root, info, token_id):
        user = info.context.user
        token = Token.objects.get(pk=token_id)
        if token.user != user:
            raise PermissionError("Token not valid")

        if EveCharacter.objects.filter(character_id=token.character_id).exists():
            corp_id = EveCharacter.objects.get(character_id=token.character_id).corporation_id
        else:
            corp_id = \
                token.get_esi_client(spec_file=SWAGGER_SPEC_PATH).Character.get_characters_character_id(
                    character_id=token.character_id).result()['corporation_id']
        try:
            corp = EveCorporationInfo.objects.get(corporation_id=corp_id)
        except EveCorporationInfo.DoesNotExist:
            corp = EveCorporationInfo.objects.create_corporation(corp_id)
        cs = CorpStats.objects.create(token=token, corp=corp)
        cs.update()
        assert cs.pk  # ensure update was successful

        return cls(ok=True)


class UpdateCorpStatsMutation(graphene.Mutation):
    class Arguments:
        corp_id = graphene.Int(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @user_passes_test(access_corpstats_test)
    def mutate(cls, root, info, corp_id):
        corp = EveCorporationInfo.objects.get(corporation_id=corp_id)
        corpstats = CorpStats.objects.get(corp=corp)
        corpstats.update()
        return cls(ok=True)


class Mutation:
    add_corpstats = AddCorpStatsMutation.Field()
    update_corpstats = UpdateCorpStatsMutation.Field()
