from django import template
from django.template.defaultfilters import stringfilter

from util.models import CategoryChoices

register = template.Library()


@register.filter
@stringfilter
def category_label(value):
    return CategoryChoices(value).label