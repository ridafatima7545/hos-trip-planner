from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from . import constants as constants
from .exceptions import TripPlanningError
from .logs import DailyLogBuilder
from .models import PlannerState, Point, RouteLeg
from .routing import RouteService


class TripPlannerService(RouteService):
    def __init__(self, log_builder: DailyLogBuilder | None = None) -> None:
        self.log_builder = log_builder or DailyLogBuilder()

    def plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        current, pickup, dropoff = self.resolve_locations(payload)
        cycle_used = self.parse_cycle(payload.get("currentCycleUsed", 0))
        start_at = self.parse_start_datetime(payload.get("startAt"))
        legs = self.build_route_legs(current, pickup, dropoff)

        state = PlannerState(cursor=start_at, cycle_used=cycle_used)
        events = self.build_events(legs, pickup, dropoff, state)
        logs = self.log_builder.split(events)

        total_miles = sum(leg.miles for leg in legs)
        total_drive_hours = sum(leg.hours for leg in legs)
        geometry = self.combine_geometry(legs)

        return {
            "inputs": {
                "currentLocation": current.label,
                "pickupLocation": pickup.label,
                "dropoffLocation": dropoff.label,
                "currentCycleUsed": cycle_used,
                "startAt": self.iso(start_at),
            },
            "summary": {
                "totalMiles": round(total_miles, 1),
                "estimatedDrivingHours": round(total_drive_hours, 2),
                "elapsedHours": round((state.cursor - start_at).total_seconds() / constants.SECONDS_PER_HOUR, 2),
                "finishAt": self.iso(state.cursor),
                "cycleUsedAtFinish": round(state.cycle_used, 2),
                "fuelStops": len([event for event in events if event["remark"] == constants.REMARK_FUEL]),
                "logDays": len(logs),
            },
            "route": {
                "geometry": [[coord[1], coord[0]] for coord in geometry],
                "legs": [self.serialize_leg(leg) for leg in legs],
            },
            "stops": self.build_stops(events, legs, total_miles),
            "events": events,
            "logs": logs,
            "assumptions": constants.ASSUMPTIONS,
        }

    def resolve_locations(self, payload: dict[str, Any]) -> tuple[Point, Point, Point]:
        return (
            self.geocode(payload.get("currentLocation", "")),
            self.geocode(payload.get("pickupLocation", "")),
            self.geocode(payload.get("dropoffLocation", "")),
        )

    def build_route_legs(self, current: Point, pickup: Point, dropoff: Point) -> list[RouteLeg]:
        first = self.route_between("current location to pickup", current, pickup, 0)
        second = self.route_between("pickup to dropoff", pickup, dropoff, first.miles)
        return [first, second]

    def build_events(
        self,
        legs: list[RouteLeg],
        pickup: Point,
        dropoff: Point,
        state: PlannerState,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        first, second = legs
        total_miles = first.miles + second.miles

        self.plan_drive_leg(events, state, first)
        self.add_on_duty(events, state, constants.PICKUP_HOURS, constants.REMARK_PICKUP, pickup.label, first.miles)
        self.plan_drive_leg(events, state, second)
        self.add_on_duty(events, state, constants.DROPOFF_HOURS, constants.REMARK_DROPOFF, dropoff.label, total_miles)
        return events

    def plan_drive_leg(self, events: list[dict[str, Any]], state: PlannerState, leg: RouteLeg) -> None:
        remaining_miles = leg.miles
        remaining_hours = leg.hours
        speed = leg.miles / leg.hours

        while remaining_hours > constants.MIN_PROGRESS_HOURS:
            self.ensure_cycle(events, state, min(constants.MIN_REQUIRED_CYCLE_HOURS, remaining_hours))

            limits = self.drive_limits(state, speed)
            chunk_hours = min(remaining_hours, *limits.values())
            if chunk_hours <= constants.MIN_PROGRESS_HOURS:
                self.resolve_drive_constraint(events, state, limits)
                continue

            miles = min(remaining_miles, chunk_hours * speed)
            self.add_drive(events, state, chunk_hours, miles, f"Drive {leg.name}", leg.name)
            remaining_hours -= chunk_hours
            remaining_miles -= miles

    def drive_limits(self, state: PlannerState, speed: float) -> dict[str, float]:
        return {
            "window": constants.MAX_DUTY_WINDOW_HOURS - state.duty_window_used,
            "drive": constants.MAX_DRIVE_SHIFT_HOURS - state.shift_drive_used,
            "break": constants.MAX_DRIVE_BEFORE_BREAK_HOURS - state.drive_since_break,
            "cycle": constants.CYCLE_LIMIT_HOURS - state.cycle_used,
            "fuel": max(0.0, (state.next_fuel_mile - state.route_mile) / speed),
        }

    def resolve_drive_constraint(
        self,
        events: list[dict[str, Any]],
        state: PlannerState,
        limits: dict[str, float],
    ) -> None:
        if limits["cycle"] <= constants.MIN_PROGRESS_HOURS:
            self.ensure_cycle(events, state, constants.MIN_REQUIRED_CYCLE_HOURS)
        elif limits["break"] <= constants.MIN_PROGRESS_HOURS:
            self.add_break(events, state)
        elif limits["drive"] <= constants.MIN_PROGRESS_HOURS:
            self.add_rest(events, state, constants.REMARK_REST_DRIVE_LIMIT)
        elif limits["window"] <= constants.MIN_PROGRESS_HOURS:
            self.add_rest(events, state, constants.REMARK_REST_DUTY_WINDOW)
        elif limits["fuel"] <= constants.MIN_PROGRESS_HOURS:
            self.add_on_duty(events, state, constants.FUEL_HOURS, constants.REMARK_FUEL, constants.REMARK_FUEL, state.route_mile)
            state.next_fuel_mile += constants.FUEL_INTERVAL_MILES
        else:
            raise TripPlanningError("Unable to make progress while planning drive time.")

    def add_event(
        self,
        events: list[dict[str, Any]],
        state: PlannerState,
        status: str,
        hours: float,
        remark: str,
        location: str | None = None,
        route_mile: float | None = None,
    ) -> None:
        if hours <= 0:
            return
        start = state.cursor
        end = start + timedelta(hours=hours)
        events.append(
            {
                "status": status,
                "start": self.iso(start),
                "end": self.iso(end),
                "hours": round(hours, 3),
                "remark": remark,
                "location": location,
                "routeMile": round(route_mile if route_mile is not None else state.route_mile, 1),
            }
        )
        state.cursor = end

    def off_duty(self, events: list[dict[str, Any]], state: PlannerState, hours: float, remark: str) -> None:
        self.add_event(events, state, constants.STATUS_OFF, hours, remark)
        if hours >= constants.REST_HOURS:
            state.duty_window_used = 0.0
            state.shift_drive_used = 0.0
            state.drive_since_break = 0.0

    def ensure_cycle(self, events: list[dict[str, Any]], state: PlannerState, needed_hours: float) -> None:
        if constants.CYCLE_LIMIT_HOURS - state.cycle_used >= needed_hours:
            return
        self.off_duty(events, state, constants.RESTART_HOURS, constants.REMARK_RESTART)
        state.cycle_used = 0.0

    def ensure_shift_window(self, events: list[dict[str, Any]], state: PlannerState, needed_hours: float) -> None:
        if state.duty_window_used + needed_hours <= constants.MAX_DUTY_WINDOW_HOURS:
            return
        self.off_duty(events, state, constants.REST_HOURS, constants.REMARK_REST_MORE_DUTY)

    def add_on_duty(
        self,
        events: list[dict[str, Any]],
        state: PlannerState,
        hours: float,
        remark: str,
        location: str,
        route_mile: float | None = None,
    ) -> None:
        self.ensure_cycle(events, state, hours)
        self.ensure_shift_window(events, state, hours)
        self.add_event(events, state, constants.STATUS_ON_DUTY, hours, remark, location, route_mile)
        state.cycle_used += hours
        state.duty_window_used += hours
        if hours >= constants.BREAK_HOURS:
            state.drive_since_break = 0.0

    def add_break(self, events: list[dict[str, Any]], state: PlannerState) -> None:
        if state.duty_window_used + constants.BREAK_HOURS > constants.MAX_DUTY_WINDOW_HOURS:
            self.add_rest(events, state, constants.REMARK_REST_BEFORE_BREAK)
            return
        self.add_event(events, state, constants.STATUS_OFF, constants.BREAK_HOURS, constants.REMARK_BREAK)
        state.duty_window_used += constants.BREAK_HOURS
        state.drive_since_break = 0.0

    def add_rest(self, events: list[dict[str, Any]], state: PlannerState, reason: str) -> None:
        self.off_duty(events, state, constants.REST_HOURS, reason)

    def add_drive(
        self,
        events: list[dict[str, Any]],
        state: PlannerState,
        hours: float,
        miles: float,
        remark: str,
        leg_name: str,
    ) -> None:
        start_mile = state.route_mile
        self.add_event(events, state, constants.STATUS_DRIVING, hours, remark, leg_name, start_mile)
        events[-1]["endRouteMile"] = round(start_mile + miles, 1)
        state.cycle_used += hours
        state.duty_window_used += hours
        state.shift_drive_used += hours
        state.drive_since_break += hours
        state.route_mile += miles

    def build_stops(self, events: list[dict[str, Any]], legs: list[RouteLeg], total_miles: float) -> list[dict[str, Any]]:
        geometry = self.combine_geometry(legs)
        stops = [
            self.make_stop("start", legs[0].start.label, legs[0].start, 0),
            self.make_stop("pickup", legs[0].end.label, legs[0].end, round(legs[0].miles, 1)),
            self.make_stop("dropoff", legs[-1].end.label, legs[-1].end, round(total_miles, 1)),
        ]

        for event in events:
            is_rest = event["status"] == constants.STATUS_OFF and ("30-minute" in event["remark"] or "10-hour" in event["remark"])
            if is_rest:
                stops.append(self.event_stop("rest", event["remark"], event, geometry, total_miles))
            if event["remark"] == constants.REMARK_FUEL:
                stops.append(self.event_stop("fuel", constants.REMARK_FUEL, event, geometry, total_miles))

        return sorted(stops, key=lambda stop: stop["routeMile"])

    def event_stop(
        self,
        stop_type: str,
        label: str,
        event: dict[str, Any],
        geometry: list[list[float]],
        total_miles: float,
    ) -> dict[str, Any]:
        point = self.interpolate_geometry(geometry, event["routeMile"], total_miles)
        return {
            "type": stop_type,
            "label": label,
            "lat": point["lat"],
            "lon": point["lon"],
            "routeMile": event["routeMile"],
            "time": event["start"],
        }

    def parse_cycle(self, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise TripPlanningError("Current cycle used must be a number of hours.") from exc
        if number < 0 or number > constants.CYCLE_LIMIT_HOURS:
            raise TripPlanningError("Current cycle used must be between 0 and 70 hours.")
        return number

    def parse_start_datetime(self, value: Any) -> datetime:
        if value:
            try:
                return datetime.fromisoformat(str(value))
            except ValueError as exc:
                raise TripPlanningError("Start date/time must be an ISO datetime.") from exc
        return datetime.combine(date.today(), time(hour=constants.DEFAULT_START_HOUR))

    @staticmethod
    def iso(dt: datetime) -> str:
        return dt.replace(microsecond=0).isoformat()

    @staticmethod
    def make_stop(stop_type: str, label: str, point: Point, route_mile: float) -> dict[str, Any]:
        return {
            "type": stop_type,
            "label": label,
            "lat": point.lat,
            "lon": point.lon,
            "routeMile": route_mile,
        }

    @staticmethod
    def serialize_leg(leg: RouteLeg) -> dict[str, Any]:
        return {
            "name": leg.name,
            "miles": round(leg.miles, 1),
            "hours": round(leg.hours, 2),
            "from": leg.start.label,
            "to": leg.end.label,
        }


def plan_trip_response(payload: dict[str, Any]) -> dict[str, Any]:
    return TripPlannerService().plan(payload)
