# Generated by Django 5.0.3 on 2025-03-01 19:48

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0003_rename_newsindexpagecontent_newsindexpage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='newspage',
            name='date',
            field=models.DateField(default=datetime.date.today, editable=False, verbose_name='Post date'),
        ),
    ]
