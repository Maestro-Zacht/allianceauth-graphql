import graphene
from graphql_jwt.decorators import login_required, permission_required

from allianceauth.srp.models import SrpFleetMain

from .types import SrpFleetMainType


class Query:
    srp_get_fleets = graphene.List(SrpFleetMainType, all=graphene.Boolean(default_value=False))

    @login_required
    @permission_required('srp.access_srp')
    def resolve_srp_get_fleets(self, info, all):
        res = SrpFleetMain.objects.all()
        if not all:
            res = res.filter(fleet_srp_status="")
        return res
