import datetime

import graphene
from graphql_jwt.decorators import login_required, permission_required
from graphene_django.forms.mutation import DjangoFormMutation

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string

from allianceauth.fleetactivitytracking.models import Fatlink, Fat
from allianceauth.fleetactivitytracking.views import SWAGGER_SPEC_PATH
from allianceauth.fleetactivitytracking.forms import FatlinkForm
from allianceauth.eveonline.models import EveCharacter
from allianceauth.eveonline.providers import provider
from esi.models import Token

from .types import FatlinkType
from ..decorators import tokens_required


class AddFatParticipation(graphene.Mutation):
    _required_scopes = [
        'esi-location.read_location.v1',
        'esi-location.read_ship_type.v1',
        'esi-universe.read_structures.v1',
        'esi-location.read_online.v1',
    ]

    class Arguments:
        token_id = graphene.ID(required=True)
        fatlink_hash = graphene.String(required=True)

    ok = graphene.Boolean()
    error = graphene.String()

    @classmethod
    @login_required
    @tokens_required(scopes=_required_scopes)
    def mutate(cls, root, info, token_id, fatlink_hash):
        try:
            token = Token.objects.all().require_scopes(' '.join(cls._required_scopes)).get(pk=token_id)
            error = None
            c = token.get_esi_client(spec_file=SWAGGER_SPEC_PATH)
            character_online = c.Location.get_characters_character_id_online(
                character_id=token.character_id
            ).result()
            character = EveCharacter.objects.get_character_by_id(token.character_id)
        except Token.DoesNotExist:
            error = 'Token not valid'
            ok = False

        if not error and character_online["online"] is True:
            fatlink = Fatlink.objects.get(hash=fatlink_hash)
            if (token.user == info.context.user) and (timezone.now() - fatlink.fatdatetime) < datetime.timedelta(seconds=(fatlink.duration * 60)):
                if character:
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

        elif not error:
            ok = False
            error = f"Cannot register the fleet participation for {character.character_name}. The character needs to be online."

        return cls(ok=ok, error=error)


class CreateFatlink(DjangoFormMutation):
    class Meta:
        form_class = FatlinkForm

    ok = graphene.Boolean()
    errors = graphene.List(graphene.String)
    fatlink = graphene.Field(FatlinkType)

    @classmethod
    @login_required
    @permission_required('auth.fleetactivitytracking')
    def perform_mutate(cls, form, info):
        fatlink = Fatlink()
        fatlink.fleet = form.cleaned_data["fleet"]
        fatlink.duration = form.cleaned_data["duration"]
        fatlink.fatdatetime = timezone.now()
        fatlink.creator = info.context.user
        fatlink.hash = get_random_string(length=15)
        try:
            fatlink.full_clean()
            fatlink.save()
            ok = True
            errors = []
        except ValidationError as e:
            form = FatlinkForm()
            errors = []
            for errorname, message in e.message_dict.items():
                errors.append(message[0].decode())
            ok = False

        return cls(ok=ok, errors=errors, fatlink=fatlink if ok else None)


class RemoveCharFatlink(graphene.Mutation):
    class Arguments:
        fat_hash = graphene.String(required=True)
        character_id = graphene.Int(required=True)

    ok = graphene.Boolean()
    fatlink = graphene.Field(FatlinkType)

    @classmethod
    @login_required
    @permission_required('auth.fleetactivitytracking')
    def mutate(cls, root, info, fat_hash, character_id):
        fatlink = Fatlink.objects.get(hash=fat_hash)
        Fat.objects.filter(fatlink=fatlink, character__character_id=character_id).delete()
        return cls(ok=True, fatlink=fatlink)


class DeleteFatlink(graphene.Mutation):
    class Arguments:
        fat_hash = graphene.String(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.fleetactivitytracking')
    def mutate(cls, root, info, fat_hash):
        Fatlink.objects.get(hash=fat_hash).delete()
        return cls(ok=True)


class Mutation:
    fat_partecipate_to_fatlink = AddFatParticipation.Field()
    fat_create_fatlink = CreateFatlink.Field()
    fat_remove_char_fat = RemoveCharFatlink.Field()
    fat_delete_fatlink = DeleteFatlink.Field()
