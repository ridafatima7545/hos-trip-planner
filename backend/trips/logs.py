from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from .constants import DAILY_TOTAL_STATUSES, SECONDS_PER_HOUR


class DailyLogBuilder:
    def split(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not events:
            return []

        start_day = datetime.fromisoformat(events[0]["start"]).date()
        end_day = datetime.fromisoformat(events[-1]["end"]).date()
        logs = []
        day = start_day

        while day <= end_day:
            log = self.build(day, events, len(logs) + 1)
            if log["segments"]:
                logs.append(log)
            day += timedelta(days=1)

        return logs

    def build(self, day: date, events: list[dict[str, Any]], day_number: int) -> dict[str, Any]:
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        segments = []
        totals = dict(DAILY_TOTAL_STATUSES)

        for event in events:
            event_start = datetime.fromisoformat(event["start"])
            event_end = datetime.fromisoformat(event["end"])
            clipped_start = max(event_start, day_start)
            clipped_end = min(event_end, day_end)
            if clipped_end <= clipped_start:
                continue

            hours = (clipped_end - clipped_start).total_seconds() / SECONDS_PER_HOUR
            totals[event["status"]] += hours
            segments.append(self.clip_event(event, event_start, event_end, clipped_start, clipped_end, day_start, hours))

        return {
            "date": day.isoformat(),
            "dayNumber": day_number,
            "segments": segments,
            "totals": {key: round(value, 2) for key, value in totals.items()},
        }

    def clip_event(
        self,
        event: dict[str, Any],
        event_start: datetime,
        event_end: datetime,
        clipped_start: datetime,
        clipped_end: datetime,
        day_start: datetime,
        hours: float,
    ) -> dict[str, Any]:
        return {
            **event,
            "startHour": round((clipped_start - day_start).total_seconds() / SECONDS_PER_HOUR, 3),
            "endHour": round((clipped_end - day_start).total_seconds() / SECONDS_PER_HOUR, 3),
            "hours": round(hours, 3),
            "routeMile": round(self.interpolate_event_mile(event, event_start, event_end, clipped_start), 1),
            "endRouteMile": round(self.interpolate_event_mile(event, event_start, event_end, clipped_end), 1),
        }

    @staticmethod
    def interpolate_event_mile(
        event: dict[str, Any],
        event_start: datetime,
        event_end: datetime,
        target: datetime,
    ) -> float:
        start_mile = float(event.get("routeMile", 0))
        end_mile = float(event.get("endRouteMile", start_mile))
        duration = (event_end - event_start).total_seconds()
        if duration <= 0:
            return start_mile
        ratio = (target - event_start).total_seconds() / duration
        return start_mile + (end_mile - start_mile) * max(0.0, min(1.0, ratio))
