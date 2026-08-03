from django.db import migrations, models


def set_2026_delegates(apps, schema_editor):
    SeasonRounds = apps.get_model("msl_about", "SeasonRounds")
    delegates_by_round = {
        "Brušperk": "Markéta Strakošová",
        "Oprechtice": "Markéta Strakošová",
        "Svinov": "Jan Černoch",
        "Metylovice": "Karel Charvát",
        "Košatka": "Robin Urban",
        "Bystřička": "Nikola Fajmanová",
        "Proskovice": "Michal Sud",
        "Petřvaldík": "Michal Sud",
        "Větřkovice": "Karel Charvát",
        "Mošnov": "Radim Tomášek",
        "Bartovice": "Mikuláš Vyhňák",
        "Jistebník": "Nikola Fajmanová",
    }

    for round_name_prefix, delegate in delegates_by_round.items():
        SeasonRounds.objects.filter(
            season_year=2026,
            round__startswith=round_name_prefix,
        ).update(delegates=delegate)


class Migration(migrations.Migration):

    dependencies = [
        ("msl_about", "0011_seasonrounds_video_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="seasonrounds",
            name="delegates",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Delegáti"),
        ),
        migrations.RunPython(set_2026_delegates, migrations.RunPython.noop),
    ]
