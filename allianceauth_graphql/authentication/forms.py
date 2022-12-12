from django import forms


class EmailRegistrationForm(forms.Form):
    email = forms.EmailField(required=True)
