from django.shortcuts import render, get_object_or_404
from django.db.models.functions import Greatest
from django.db.models import Case, When, IntegerField

from msl_about.models import SeasonRounds
from msl_results.models import Result
from util.models import CategoryChoices


def round_detail(request, round_id, category):
    round_obj = get_object_or_404(SeasonRounds, id=round_id)

    try:
        results = Result.objects.filter(round=round_obj, team__category=category).annotate(
            max_lp_pp=Greatest('lp', 'pp'),
            sort_column=Case(
                When(lp=0, then=9999),
                When(pp=0, then=9999),
                default='max_lp_pp',
                output_field=IntegerField()
            )
        ).order_by('sort_column')
    except Result.DoesNotExist:
        results = None

    # Get the ResultsPage for the link
    from msl_results.models import ResultsPage
    results_page = ResultsPage.objects.live().first()

    context = {
        'round': round_obj,
        'results': results,
        'category': CategoryChoices(category),
        'results_page': results_page,
    }

    return render(request, 'msl_results/round_detail.html', context)
