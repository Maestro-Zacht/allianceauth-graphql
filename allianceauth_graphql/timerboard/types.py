import graphene
from graphene_django import DjangoObjectType

from allianceauth.timerboard.models import Timer, TimerType


TimerStructureChoices = graphene.Enum('TimerStructureChoices', [('POCO', 'POCO'),
                                                                ('I_HUB', 'I-HUB'),
                                                                ('TCU', 'TCU'),
                                                                ('POS_S', 'POS[S]'),
                                                                ('POS_M', 'POS[M]'),
                                                                ('POS_L', 'POS[L]'),
                                                                ('Astrahus', 'Astrahus'),
                                                                ('Fortizar', 'Fortizar'),
                                                                ('Keepstar', 'Keepstar'),
                                                                ('Raitaru', 'Raitaru'),
                                                                ('Azbel', 'Azbel'),
                                                                ('Sotiyo', 'Sotiyo'),
                                                                ('Athanor', 'Athanor'),
                                                                ('Tatara', 'Tatara'),
                                                                ('Pharolux_Cyno_Beacon', 'Pharolux Cyno Beacon'),
                                                                ('Tenebrex_Cyno_Jammer', 'Tenebrex Cyno Jammer'),
                                                                ('Ansiblex_Jump_Gate', 'Ansiblex Jump Gate'),
                                                                ('Moon_Mining_Cycle', 'Moon Mining Cycle'),
                                                                ('Other', 'Other')])
TimerObjectiveChoices = graphene.Enum('TimerObjectiveChoices', [('Friendly', 'Friendly'),
                                                                ('Hostile', 'Hostile'),
                                                                ('Neutral', 'Neutral')])
TimerTypeChoices = graphene.Enum.from_enum(TimerType)


class StructureTimerType(DjangoObjectType):
    class Meta:
        model = Timer
        exclude = ('eve_corp', 'eve_character',)
