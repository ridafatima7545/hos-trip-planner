from datetime import datetime
from unittest.mock import patch

from django.test import SimpleTestCase

from .services import Point, RouteLeg, TripPlannerService, plan_trip_response


def fake_geocode(place):
    lookup = {
        "A": Point(lat=41.8781, lon=-87.6298, label="A"),
        "B": Point(lat=39.7684, lon=-86.1581, label="B"),
        "C": Point(lat=32.7767, lon=-96.7970, label="C"),
    }
    return lookup[place]


def fake_route(name, start, end, route_mile_start):
    if end.label == "B":
        miles, hours = 200, 4
    else:
        miles, hours = 1400, 24
    return RouteLeg(
        name=name,
        start=start,
        end=end,
        miles=miles,
        hours=hours,
        geometry=[[start.lon, start.lat], [end.lon, end.lat]],
        route_mile_start=route_mile_start,
    )


class TripPlannerTests(SimpleTestCase):
    @patch.object(TripPlannerService, "request_json", side_effect=Exception("route unavailable"))
    def test_route_between_builds_route_leg_with_correct_field_types(self, *_):
        service = TripPlannerService()
        start = Point(lat=41.8781, lon=-87.6298, label="A")
        end = Point(lat=39.7684, lon=-86.1581, label="B")

        leg = service.route_between("A to B", start, end, 0)

        self.assertEqual(leg.name, "A to B")
        self.assertIs(leg.start, start)
        self.assertIs(leg.end, end)
        self.assertIsInstance(leg.miles, float)
        self.assertIsInstance(leg.hours, float)
        self.assertIsInstance(leg.geometry, list)

    @patch.object(TripPlannerService, "route_between", side_effect=fake_route)
    @patch.object(TripPlannerService, "geocode", side_effect=fake_geocode)
    def test_long_trip_inserts_fuel_rests_and_logs(self, *_):
        result = plan_trip_response(
            {
                "currentLocation": "A",
                "pickupLocation": "B",
                "dropoffLocation": "C",
                "currentCycleUsed": 10,
                "startAt": "2026-07-06T08:00:00",
            }
        )

        remarks = [event["remark"] for event in result["events"]]
        self.assertIn("Fuel stop", remarks)
        self.assertTrue(any("10-hour off-duty reset" in remark for remark in remarks))
        self.assertGreaterEqual(result["summary"]["logDays"], 2)

    @patch.object(TripPlannerService, "route_between", side_effect=fake_route)
    @patch.object(TripPlannerService, "geocode", side_effect=fake_geocode)
    def test_exhausted_cycle_gets_restart_before_work(self, *_):
        result = plan_trip_response(
            {
                "currentLocation": "A",
                "pickupLocation": "B",
                "dropoffLocation": "C",
                "currentCycleUsed": 70,
                "startAt": "2026-07-06T08:00:00",
            }
        )

        self.assertEqual(result["events"][0]["status"], "OFF")
        self.assertIn("34-hour restart", result["events"][0]["remark"])
        finish = datetime.fromisoformat(result["summary"]["finishAt"])
        self.assertGreater(finish, datetime.fromisoformat("2026-07-07T18:00:00"))
