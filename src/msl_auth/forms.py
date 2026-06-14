from django import forms
from django.core.validators import RegexValidator


class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField(
        label="E-mailová adresa",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "vas@email.cz",
            "autocomplete": "email",
        }),
    )


class DisplayNameForm(forms.Form):
    display_name = forms.CharField(
        label="Uživatelské jméno",
        min_length=3,
        max_length=30,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9_.\-]+$",
                message="Povolena jsou pouze písmena, číslice a znaky . _ -",
            ),
        ],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "např. honza42",
            "autocomplete": "off",
        }),
        help_text="3–30 znaků. Bude veřejně zobrazeno místo vaší e-mailové adresy.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_display_name(self):
        from .models import UserProfile

        value = self.cleaned_data["display_name"].strip()
        qs = UserProfile.objects.filter(display_name__iexact=value)
        if self.user is not None:
            qs = qs.exclude(user=self.user)
        if qs.exists():
            raise forms.ValidationError("Toto uživatelské jméno je již obsazené.")
        return value
