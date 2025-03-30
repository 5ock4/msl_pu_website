from django.db import models
from django.shortcuts import render, redirect
from django.contrib import messages

from wagtail.models import Page

from msl_about.models import Team
from msl_enroll.forms import EnrollForm


# Create your models here.
class EnrollPage(Page):
    def serve(self, request):
        if request.method == 'POST':
            form = EnrollForm(request.POST)
            if form.is_valid():
                try:
                    team = Team.objects.create(
                        name=form.cleaned_data.get('team'),
                        category=form.cleaned_data.get('category'),
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
