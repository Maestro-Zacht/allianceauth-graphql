from django import forms

from allianceauth.optimer.form import OpForm


class EditOpForm(OpForm):
    op_id = forms.IntegerField(required=True)
