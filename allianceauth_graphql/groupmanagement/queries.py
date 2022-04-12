import graphene
from graphql_jwt.decorators import login_required

from django.db.models import Case, When, Exists, OuterRef, Q

from allianceauth.groupmanagement.managers import GroupManager
from allianceauth.groupmanagement.models import AuthGroup, GroupRequest

from .types import AuthGroupType


class Query:
    user_joinable_groups = graphene.List(AuthGroupType)

    @login_required
    def resolve_user_joinable_groups(self, info):
        user = info.context.user
        groups_qs = GroupManager.get_joinable_groups_for_user(user, include_hidden=False)
        auth_groups = AuthGroup.objects.filter(group__in=groups_qs).order_by('group__name')

        return auth_groups.annotate(
            application=Case(
                When(
                    Exists(user.groups.filter(pk=OuterRef('group_id'))),
                    then=Case(
                        When(
                            Exists(GroupRequest.objects.filter(user=user, group_id=OuterRef('group_id'))),
                            then=2
                        ),
                        default=1
                    )
                ),
                When(
                    ~Exists(GroupRequest.objects.filter(user=user, group_id=OuterRef('group_id'))),
                    then=Case(
                        When(
                            Q(open=True), then=3
                        ),
                        default=4
                    )
                ),
                default=2
            )
        )
