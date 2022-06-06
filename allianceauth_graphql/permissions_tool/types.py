from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType

import graphene
from graphene_django import DjangoObjectType

from allianceauth.authentication.models import State


class ContentTypeType(DjangoObjectType):
    class Meta:
        model = ContentType
        fields = ('app_label', 'model',)


class GroupAdminType(DjangoObjectType):
    class Meta:
        model = Group
        fields = ('name', 'authgroup', 'id', 'user_set',)


class StateAdminType(DjangoObjectType):
    class Meta:
        model = State
        fields = ('name', 'userprofile_set',)


class PermissionType(DjangoObjectType):
    num_users = graphene.Int()
    num_groups = graphene.Int()
    num_users_in_groups = graphene.Int()
    num_states = graphene.Int()
    num_users_in_states = graphene.Int()

    group_set = graphene.List(GroupAdminType, required=True)
    state_set = graphene.List(StateAdminType, required=True)

    class Meta:
        model = Permission
        fields = (
            'id',
            'name',
            'codename',
            'content_type',
            'user_set',
            'state_set',
            'group_set',
        )


class AppModelType(graphene.ObjectType):
    app_label = graphene.String(required=True)
    model = graphene.String(required=True)
