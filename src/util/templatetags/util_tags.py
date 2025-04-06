import random
from django import template

from msl_about.models import AboutMSLPage, EnrollmentsPage, RoundsPage

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

@register.simple_tag(takes_context=False)
def get_rounds_page():
    """Get the Rounds page."""
    try:
        return RoundsPage.objects.live().first()
    except:
        return None