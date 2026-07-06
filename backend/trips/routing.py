from __future__ import annotations

import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .constants import (
    EARTH_RADIUS_MILES,
    FALLBACK_SPEED_MPH,
    METERS_PER_MILE,
    NOMINATIM_URL,
    OSRM_URL,
    REQUEST_TIMEOUT_SECONDS,
    ROAD_DISTANCE_FALLBACK_MULTIPLIER,
    SECONDS_PER_HOUR,
    USER_AGENT,
)
from .exceptions import TripPlanningError
from .models import Point, RouteLeg


class RouteService:
    def request_json(self, url: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise TripPlanningError(str(exc)) from exc

    def geocode(self, place: str) -> Point:
        cleaned = (place or "").strip()
        if not cleaned:
            raise TripPlanningError("All location fields are required.")

        params = urlencode({"format": "json", "limit": 1, "q": cleaned})
        data = self.request_json(f"{NOMINATIM_URL}?{params}")
        if not data:
            raise TripPlanningError(f"Could not find coordinates for '{cleaned}'.")

        item = data[0]
        label = item.get("display_name", cleaned).split(",")[0]
        return Point(lat=float(item["lat"]), lon=float(item["lon"]), label=label)

    def route_between(self, name: str, start: Point, end: Point, route_mile_start: float) -> RouteLeg:
        url = (
            f"{OSRM_URL}/{start.lon},{start.lat};{end.lon},{end.lat}"
            "?overview=full&geometries=geojson&alternatives=false&steps=false"
        )
        try:
            data = self.request_json(url)
            route = data["routes"][0]
            miles = float(route["distance"]) / METERS_PER_MILE
            hours = float(route["duration"]) / SECONDS_PER_HOUR
            geometry = route["geometry"]["coordinates"]
        except Exception:
            miles = self.haversine_miles(start, end) * ROAD_DISTANCE_FALLBACK_MULTIPLIER
            hours = miles / FALLBACK_SPEED_MPH
            geometry = [[start.lon, start.lat], [end.lon, end.lat]]

        if miles <= 0 or hours <= 0:
            raise TripPlanningError(f"Could not calculate a route for {name}.")

        return RouteLeg(
            name=name,
            start=start,
            end=end,
            miles=miles,
            hours=hours,
            geometry=geometry,
            route_mile_start=route_mile_start,
        )

    def interpolate_geometry(self, route: list[list[float]], target_mile: float, total_miles: float) -> dict[str, float]:
        if not route:
            return {"lat": 0.0, "lon": 0.0}
        if len(route) == 1 or total_miles <= 0:
            return {"lat": route[0][1], "lon": route[0][0]}

        distances = []
        total = 0.0
        for index in range(1, len(route)):
            a = Point(lat=route[index - 1][1], lon=route[index - 1][0], label="")
            b = Point(lat=route[index][1], lon=route[index][0], label="")
            total += self.haversine_miles(a, b)
            distances.append(total)

        desired = (target_mile / total_miles) * total if total else 0
        prev_dist = 0.0
        for index, dist in enumerate(distances, start=1):
            if dist >= desired:
                segment = max(0.001, dist - prev_dist)
                ratio = max(0.0, min(1.0, (desired - prev_dist) / segment))
                lon = route[index - 1][0] + (route[index][0] - route[index - 1][0]) * ratio
                lat = route[index - 1][1] + (route[index][1] - route[index - 1][1]) * ratio
                return {"lat": lat, "lon": lon}
            prev_dist = dist
        return {"lat": route[-1][1], "lon": route[-1][0]}

    @staticmethod
    def haversine_miles(a: Point, b: Point) -> float:
        lat1, lon1, lat2, lon2 = map(math.radians, [a.lat, a.lon, b.lat, b.lon])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(x))

    @staticmethod
    def combine_geometry(legs: list[RouteLeg]) -> list[list[float]]:
        geometry = []
        for leg in legs:
            geometry.extend(leg.geometry if not geometry else leg.geometry[1:])
        return geometry
