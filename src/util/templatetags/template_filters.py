from django import template
from django.template.defaultfilters import stringfilter

from util.models import CategoryChoices

register = template.Library()


@register.filter
@stringfilter
def category_label(value):
    return CategoryChoices(value).label


@register.filter
def to_roman(value):
    """Convert integer to Roman numeral."""
    if not isinstance(value, int) or value <= 0:
        return value
    
    values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    symbols = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    
    result = ""
    for i in range(len(values)):
        count = value // values[i]
        if count:
            result += symbols[i] * count
            value -= values[i] * count
    return result