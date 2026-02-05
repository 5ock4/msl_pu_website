import random
from django import template

from msl_about.models import AboutMSLPage, EnrollmentsPage, RoundsPage, SeasonParameters, SeasonRounds
from msl_results.models import ResultsPage
from util.models import CategoryChoices

register = template.Library()


@register.simple_tag()
def random_1_to_300():
    return random.randint(1, 300)

@register.simple_tag()
def is_msl_about_page(object):
    return isinstance(object, AboutMSLPage)

@register.inclusion_tag('msl_about/enrollments_page.html', takes_context=True)
def show_enrollments(context):
    request = context['request']
    try:
        enrollments_page = EnrollmentsPage.objects.first()
        if enrollments_page:
            # Use the page's own get_context method
            page_context = enrollments_page.get_context(request)
            page_context.update({
                'enrollments_page': enrollments_page,
            })
            return page_context
    except:
        pass
    return {'enrollments_filtered': []}

@register.inclusion_tag('msl_results/results_card.html', takes_context=True)
def show_results(context):
    request = context['request']
    try:
        results_page = ResultsPage.objects.first()
        if results_page:
            # Use the page's own get_context method
            page_context = results_page.get_context(request)
            page_context.update({
                'results_page': results_page,
            })
            return page_context
    except:
        pass
    return {'results_filtered': []}

@register.simple_tag(takes_context=False)
def get_rounds_page():
    """Get the Rounds page."""
    try:
        return RoundsPage.objects.live().first()
    except:
        return None

@register.simple_tag
def get_season_params_years():
    return SeasonParameters.objects.values_list('season_year', flat=True).distinct().order_by('-season_year')

@register.simple_tag
def get_season_rounds_years():
    return SeasonRounds.objects.values_list('season_year', flat=True).distinct().order_by('-season_year')

@register.simple_tag(takes_context=True)
def get_categories(context):
    if "season_year" in context:
        season_year = context["season_year"]
        available_categories = SeasonParameters.objects.filter(season_year=season_year).values_list('category', flat=True).distinct()
    else:
        available_categories = SeasonParameters.objects.values_list('category', flat=True).distinct()

    # Define the desired order using CategoryChoices
    category_order = [CategoryChoices.MUZI, CategoryChoices.ZENY, CategoryChoices.VETERANI]

    # Filter and sort categories based on the defined order, return tuples with value and label
    ordered_categories = [(cat, CategoryChoices(cat).label) for cat in category_order if cat in available_categories]

    return ordered_categories

@register.simple_tag(takes_context=True)
def is_wagtail_admin(context):
    """Check if the current user is a Wagtail admin user."""
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    return request.user.is_staff or request.user.is_superuser or request.user.username == 'RadaMSL'
