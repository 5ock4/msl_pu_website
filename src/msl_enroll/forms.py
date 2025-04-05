from django import forms

from msl_about.models import CategoryChoices


class EnrollForm(forms.Form):
    team = forms.CharField(label="Tým", max_length=100)
    category = forms.ChoiceField(
        label="Kategorie",
        choices=CategoryChoices.choices
    )
