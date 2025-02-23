from datetime import date

from django.db import models

# Add these:
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

from wagtail.search import index


class NewsIndexPage(Page): ...


class NewsPage(Page):
    date = models.DateField("Post date", default=date.today, editable=False)
    author = models.CharField(max_length=20)
    body = RichTextField(blank=True)

    search_fields = Page.search_fields + [
        index.SearchField("author"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("author"),
        FieldPanel("body"),
    ]
