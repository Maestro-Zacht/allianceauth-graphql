from graphene_django import DjangoObjectType
from allianceauth.authentication.models import UserProfile


class UserProfileType(DjangoObjectType):
    class Meta:
        model = UserProfile
