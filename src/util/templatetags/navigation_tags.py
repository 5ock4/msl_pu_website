from django import template
from wagtail.models import Site, Page

from msl_about.models import SeasonParameters, SeasonRounds


register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context):
    return Site.find_for_request(context["request"]).root_page

# TODO: maybe delete this in future - getting pages dynamically should be enough for the menu
@register.simple_tag(takes_context=True)
def get_news(context):
    root_page: Page = Site.find_for_request(context["request"]).root_page
    try:
        news_page: Page = root_page.get_children().filter(title="Aktuality")[0]  # TODO: implement some EN:CZ translation dict
    except IndexError:
        news_page = None
    return news_page

@register.simple_tag(takes_context=True)
def get_enrollment_page(context):
    root_page: Page = Site.find_for_request(context["request"]).root_page
    try:
        enrollment_page: Page = root_page \
            .get_children() \
            .filter(title="O MS lize")[0] \
            .get_children() \
            .filter(title=f"Přihlášené týmy do MSL 2025")

    except IndexError:
        enrollment_page = None
    return enrollment_page

@register.simple_tag
def get_season_params_years():
    return SeasonParameters.objects.values_list('season_year', flat=True).distinct().order_by('-season_year')

@register.simple_tag
def get_season_rounds_years():
    return SeasonRounds.objects.values_list('season_year', flat=True).distinct().order_by('-season_year')
