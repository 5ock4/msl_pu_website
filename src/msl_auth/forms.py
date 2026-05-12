from django import forms


class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField(
        label="E-mailová adresa",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "vas@email.cz",
            "autocomplete": "email",
        }),
    )
