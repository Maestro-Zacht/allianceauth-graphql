from django import forms
from allianceauth.srp.form import SrpFleetUserRequestForm


class GQLSrpFleetUserRequestForm(SrpFleetUserRequestForm):
    fleet_srp_code = forms.CharField(max_length=254, required=True)
