import graphene
from graphene_django import DjangoObjectType
from allianceauth.authentication.models import UserProfile, State, CharacterOwnership
from django.contrib.auth.models import Group, User


class StateType(DjangoObjectType):
    class Meta:
        model = State
        fields = ('name', )


class UserProfileType(DjangoObjectType):
    state = graphene.Field(StateType, required=True)

    class Meta:
        model = UserProfile


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'username', 'profile', 'character_ownerships',)


class GroupStatusEnum(graphene.Enum):
    JOINED = 1
    PENDING = 2
    CAN_JOIN = 3
    CAN_APPLY = 4


class GroupType(DjangoObjectType):
    status = graphene.Field(GroupStatusEnum)
    num_members = graphene.Int()

    class Meta:
        model = Group
        fields = ('name', 'authgroup', 'id',)


class CharacterOwnershipType(DjangoObjectType):
    class Meta:
        model = CharacterOwnership
        fields = ('character', 'user',)


class LoginStatus(graphene.Enum):
    ERROR = 0
    LOGGED_IN = 1
    REGISTRATION = 2
