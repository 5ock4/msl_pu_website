from django.db import models

# Add these:
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

from wagtail.search import index


class NewsIndexPage(Page): ...


class NewsPage(Page):
    date = models.DateField("Post date")
    author = models.CharField(max_length=20)
    body = RichTextField(blank=True)

    search_fields = Page.search_fields + [
        index.SearchField("author"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("date"),
        FieldPanel("author"),
        FieldPanel("body"),
    ]
