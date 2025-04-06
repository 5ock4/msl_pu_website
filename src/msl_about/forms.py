from django import forms
from django.utils.safestring import mark_safe

from util.models import CategoryChoices



class EnrollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    new_team = forms.CharField(
        label="Název týmu", 
        max_length=100,
        localize=True,
        required=True,
    )
    category = forms.ChoiceField(
        label="Kategorie",
        choices=CategoryChoices.choices,
    )
    team_representative = forms.CharField(
        label="Jméno a příjmení zástupce týmu", 
        max_length=100,
    )
    team_representative_email = forms.EmailField(
        label="E-mail zástupce týmu",
    )
    agree_to_terms = forms.BooleanField(
        label=mark_safe(
            'Souhlasím s <a href="/gdpr/" target="_blank">podmínkami ochrany osobních údajů</a>'
            ' a <a href="/o-ms-lize/dokumenty/" target="_blank">pravidly soutěže</a>.'
        ),
        required=True,
    )
