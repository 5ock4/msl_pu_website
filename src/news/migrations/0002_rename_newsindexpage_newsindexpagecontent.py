# Generated by Django 5.0.3 on 2025-02-08 15:05

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="NewsIndexPage",
            new_name="NewsIndexPageContent",
        ),
    ]
