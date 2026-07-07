from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('msl_about', '0010_results_excel_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='seasonrounds',
            name='video_url',
            field=models.URLField(blank=True, default='', verbose_name='Odkaz na videa'),
        ),
    ]
