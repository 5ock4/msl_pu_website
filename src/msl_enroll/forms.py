from django import forms
from django.utils.safestring import mark_safe

from msl_about.models import CategoryChoices, Team


class EnrollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get all teams from the database and create choices
        team_choices = [('', '---------')] + [(team.id, str(team)) for team in Team.objects.all().order_by('name')]
        self.fields['team'].choices = team_choices

    team = forms.ChoiceField(
        label="Tým", 
        required=False,
    )
    new_team = forms.CharField(
        label="Nový tým", 
        max_length=100,
        localize=True,
        required=False,
    )
    category = forms.ChoiceField(
        label="Kategorie",
        choices=CategoryChoices.choices,
    )
    team_representative = forms.CharField(
        label="Zástupce týmu", 
        max_length=100,
    )
    team_representative_email = forms.EmailField(
        label="E-mail",
    )
    agree_to_terms = forms.BooleanField(
        label=mark_safe(
            'Souhlasím s <a href="/gdpr/" target="_blank">podmínkami ochrany osobních údajů</a>'
            ' a <a href="/pravidla-souteze/" target="_blank">pravidly soutěže</a>.'
        ),
        required=True,
    )

    def clean(self):
        cleaned_data = super().clean()
        team_id = cleaned_data.get('team')
        new_team = cleaned_data.get('new_team')
        
        if not team_id and not new_team:
            raise forms.ValidationError("Je nutné vybrat existující tým nebo zadat nový")

        return cleaned_data
