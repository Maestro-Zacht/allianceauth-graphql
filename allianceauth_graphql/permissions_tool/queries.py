from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, Q

import graphene
from graphql_jwt.decorators import login_required, permission_required

from .types import PermissionType, AppModelType


class Query:
    perms_search = graphene.List(
        PermissionType,
        app_label=graphene.String(),
        model=graphene.String(),
        search_string=graphene.String(),
        show_only_applied=graphene.Boolean(default_value=True)
    )

    perms_list_app_models = graphene.List(AppModelType)

    @login_required
    @permission_required('permissions_tool.audit_permissions')
    def resolve_perms_search(self, info, show_only_applied, app_label=None, model=None, search_string=None):
        perms = (
            Permission.objects.all()
            .annotate(num_users=Count('user', distinct=True))
            .annotate(num_groups=Count('group', distinct=True))
            .annotate(num_users_in_groups=Count('group__user', distinct=True))
            .annotate(num_states=Count('state', distinct=True))
            .annotate(num_users_in_states=Count('state__userprofile', distinct=True))
        )

        if show_only_applied:
            perms = perms.alias(num_entities=F('num_users') + F('num_groups') + F('num_states'))\
                .filter(num_entities__gt=0)

        if app_label:
            perms = perms.filter(content_type__app_label__icontains=app_label)

        if model:
            perms = perms.filter(content_type__model__icontains=model)

        if search_string:
            perms = perms.filter(
                Q(content_type__app_label__icontains=search_string) |
                Q(content_type__model__icontains=search_string) |
                Q(name__icontains=search_string) |
                Q(codename__icontains=search_string)
            )

        return perms

    @login_required
    @permission_required('permissions_tool.audit_permissions')
    def resolve_perms_list_app_models(self, info):
        return ContentType.objects.values('app_label', 'model')
