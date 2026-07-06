import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PlannerState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cursor", models.DateTimeField()),
                ("cycle_used", models.FloatField()),
                ("duty_window_used", models.FloatField(default=0.0)),
                ("shift_drive_used", models.FloatField(default=0.0)),
                ("drive_since_break", models.FloatField(default=0.0)),
                ("route_mile", models.FloatField(default=0.0)),
                ("next_fuel_mile", models.FloatField(default=1000.0)),
            ],
        ),
        migrations.CreateModel(
            name="Point",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lat", models.FloatField()),
                ("lon", models.FloatField()),
                ("label", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="RouteLeg",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("miles", models.FloatField()),
                ("hours", models.FloatField()),
                ("geometry", models.JSONField(default=list)),
                ("route_mile_start", models.FloatField(default=0.0)),
                (
                    "end",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_leg_ends",
                        to="trips.point",
                    ),
                ),
                (
                    "start",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_leg_starts",
                        to="trips.point",
                    ),
                ),
            ],
        ),
    ]
