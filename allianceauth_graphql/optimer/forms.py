from django import forms

from allianceauth.optimer.form import OpForm


class EditOpForm(OpForm):
    id = forms.IntegerField(required=True)
