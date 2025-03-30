import random
from django import template

from msl_about.models import AboutMSLPage


register = template.Library()


@register.simple_tag()
def random_1_to_300():
    return random.randint(1, 300)

@register.simple_tag()
def is_msl_about_page(object):
    return isinstance(object, AboutMSLPage)
