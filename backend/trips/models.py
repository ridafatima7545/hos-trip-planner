from django.db import models

from .constants import FUEL_INTERVAL_MILES


class Point(models.Model):
    lat = models.FloatField()
    lon = models.FloatField()
    label = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.label


class RouteLeg(models.Model):
    name = models.CharField(max_length=255)
    start = models.ForeignKey(Point, on_delete=models.CASCADE, related_name="route_leg_starts")
    end = models.ForeignKey(Point, on_delete=models.CASCADE, related_name="route_leg_ends")
    miles = models.FloatField()
    hours = models.FloatField()
    geometry = models.JSONField(default=list)
    route_mile_start = models.FloatField(default=0.0)

    def __str__(self) -> str:
        return f"{self.start} to {self.end}"


class PlannerState(models.Model):
    cursor = models.DateTimeField()
    cycle_used = models.FloatField()
    duty_window_used = models.FloatField(default=0.0)
    shift_drive_used = models.FloatField(default=0.0)
    drive_since_break = models.FloatField(default=0.0)
    route_mile = models.FloatField(default=0.0)
    next_fuel_mile = models.FloatField(default=FUEL_INTERVAL_MILES)
