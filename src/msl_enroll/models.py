import datetime as dt
from xml.dom.domreg import registered

from django.db import models
from django.shortcuts import render, redirect
from django.contrib import messages

from wagtail.models import Page
from wagtail.admin.panels import FieldPanel

from msl_about.models import SeasonTeams, Team
from msl_enroll.forms import EnrollForm


# Create your models here.
class EnrollPage(Page):
    year = models.IntegerField(
        verbose_name="Ročník",
        help_text="Ročník, do kterého se tým přihlašuje.",
        default=2025,
    )

    content_panels = Page.content_panels + [
        FieldPanel('year'),
    ]

    def serve(self, request):
        if request.method == 'POST':
            form = EnrollForm(request.POST)
            if form.is_valid():
                try:
                    team_id: int | None = form.cleaned_data.get('team')
                    if team_id:
                        team = Team.objects.get(id=team_id)
                    else:
                        team = Team.objects.create(
                            name=form.cleaned_data['new_team'],
                            category=form.cleaned_data['category'],
                        )
                    SeasonTeams.objects.create(
                        season_year=self.year,
                        team=team,
                        team_representative=form.cleaned_data['team_representative'],
                        team_representative_email=form.cleaned_data['team_representative_email'],
                        registered=True,
                        date_registration=dt.date.today(),
                    )
                    messages.success(request, f'Tým {team.name} byl úspěšně přihlášen do MSL!')
                except Exception as e:
                    # Handle any errors (e.g., unique constraint violation)
                    messages.error(request, f'Nastala chyba při přihlašování týmu: {str(e)}')

                return redirect(self.url)  # TOOD: redirect somewhere else
        else:
            form = EnrollForm()

        return render(request, 'msl_enroll/enroll_page.html', {
            'page': self,
            'form': form,
        })
