from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
import numpy as np
import pandas as pd

from msl_results.models import Result
from msl_results.round_results_preprocessor import RoundResultsPreprocessor
from .models import SeasonRounds, RoundsPage
from util.models import CategoryChoices


def is_wagtail_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.username == 'RadaMSL')

@user_passes_test(is_wagtail_admin)
def upload_results(request, round_id):
    round_obj = get_object_or_404(SeasonRounds, id=round_id)
    
    if request.method == 'POST' and request.FILES.get('results_file'):
        round_results_manipulator = RoundResultsPreprocessor(round_obj, request.FILES['results_file'])
        round_results_manipulator.store_to_results_model()

        messages.success(request, f'Výsledky pro kolo {round_obj.round} úspěšně vloženy!')

    # Redirect back to the rounds page
    try:
        rounds_page = RoundsPage.objects.live().first()
        if rounds_page:
            return redirect(rounds_page.url)
    except:
        pass
    
    # Fallback redirect
    return redirect('/')
