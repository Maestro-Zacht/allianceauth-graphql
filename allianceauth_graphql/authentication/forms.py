from django import forms


class EmailRegistrationForm(forms.Form):
    email = forms.EmailField(required=True)
    token = forms.CharField(required=True)
