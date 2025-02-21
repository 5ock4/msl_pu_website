from django import template
from wagtail.models import Site, Page


register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context):
    return Site.find_for_request(context["request"]).root_page

# TODO: maybe delete this in future - getting pages dynamically should be enough for the menu
@register.simple_tag(takes_context=True)
def get_news(context):
    root_page: Page = Site.find_for_request(context["request"]).root_page
    news_page: Page = root_page.get_children().filter(title="Aktuality")[0]  # TODO: implement some EN:CZ translation dict
    return news_page