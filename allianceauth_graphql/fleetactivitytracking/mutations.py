import datetime

import graphene
from graphql_jwt.decorators import login_required

from django.utils import timezone
from django.core.exceptions import ValidationError

from allianceauth.fleetactivitytracking.models import Fatlink, Fat
from allianceauth.fleetactivitytracking.views import SWAGGER_SPEC_PATH
from allianceauth.eveonline.models import EveCharacter
from allianceauth.eveonline.providers import provider
from esi.models import Token

from ..decorators import tokens_required


class AddFatParticipation(graphene.Mutation):
    class Arguments:
        token_id = graphene.ID(required=True)
        fatlink_hash = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @tokens_required(scopes=['esi-location.read_location.v1', 'esi-location.read_ship_type.v1', 'esi-universe.read_structures.v1'])
    def mutate(cls, root, info, token_id, fatlink_hash):
        fatlink = Fatlink.objects.get(hash=fatlink_hash)
        token = Token.objects.get(pk=token_id)

        if (token.user == info.context.user) and (timezone.now() - fatlink.fatdatetime) < datetime.timedelta(seconds=(fatlink.duration * 60)):
            character = EveCharacter.objects.get_character_by_id(token.character_id)

            if character:
                c = token.get_esi_client(spec_file=SWAGGER_SPEC_PATH)
                location = c.Location.get_characters_character_id_location(character_id=token.character_id).result()
                ship = c.Location.get_characters_character_id_ship(character_id=token.character_id).result()
                location['solar_system_name'] = \
                    c.Universe.get_universe_systems_system_id(system_id=location['solar_system_id']).result()['name']
                if location['station_id']:
                    location['station_name'] = \
                        c.Universe.get_universe_stations_station_id(station_id=location['station_id']).result()['name']
                elif location['structure_id']:
                    location['station_name'] = \
                        c.Universe.get_universe_structures_structure_id(structure_id=location['structure_id']).result()[
                            'name']
                else:
                    location['station_name'] = "No Station"
                ship['ship_type_name'] = provider.get_itemtype(ship['ship_type_id']).name

                fat = Fat()
                fat.system = location['solar_system_name']
                fat.station = location['station_name']
                fat.shiptype = ship['ship_type_name']
                fat.fatlink = fatlink
                fat.character = character
                fat.user = info.context.user
                try:
                    fat.full_clean()
                    fat.save()
                    ok = True
                    error = None
                except ValidationError as e:
                    err_messages = []
                    for errorname, message in e.message_dict.items():
                        err_messages.append(message[0])
                    error = ' '.join(err_messages)
                    ok = False
            else:
                ok = False
                error = "Character doesn't exists"
        else:
            ok = False
            error = "FAT link has expired or user not valid"


class Mutation:
    pass
