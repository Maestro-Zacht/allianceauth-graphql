import graphene
from graphene_django import DjangoObjectType
from allianceauth.authentication.models import UserProfile, State
from django.contrib.auth.models import Group


class StateType(DjangoObjectType):
    class Meta:
        model = State
        fields = ('name', )


class UserProfileType(DjangoObjectType):
    class Meta:
        model = UserProfile


class GroupType(DjangoObjectType):
    class Meta:
        model = Group


class LoginStatus(graphene.Enum):
    ERROR = 0
    LOGGED_IN = 1
    REGISTRATION = 2
