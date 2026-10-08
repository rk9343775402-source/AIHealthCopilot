from __future__ import annotations

import math
from typing import Any

import httpx


class LocationSearchError(RuntimeError):
    pass


class LocationService:
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    @staticmethod
    def _distance_km(latitude: float, longitude: float, other_lat: float, other_lon: float) -> float:
        earth_radius_km = 6371.0
        lat1, lat2 = math.radians(latitude), math.radians(other_lat)
        delta_lat = math.radians(other_lat - latitude)
        delta_lon = math.radians(other_lon - longitude)
        arc = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        return earth_radius_km * 2 * math.atan2(math.sqrt(arc), math.sqrt(1 - arc))

    async def nearby_care(self, latitude: float, longitude: float, radius_m: int = 10000) -> list[dict[str, Any]]:
        query = (
            "[out:json][timeout:15];"
            f"(node(around:{radius_m},{latitude},{longitude})[amenity~\"^(hospital|clinic|doctors)$\"];"
            f"way(around:{radius_m},{latitude},{longitude})[amenity~\"^(hospital|clinic|doctors)$\"];"
            f"relation(around:{radius_m},{latitude},{longitude})[amenity~\"^(hospital|clinic|doctors)$\"];);"
            "out center tags;"
        )
        try:
            async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "AIHealthCopilot/1.0"}) as client:
                response = await client.post(self.OVERPASS_URL, data={"data": query})
                response.raise_for_status()
                elements = response.json().get("elements", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise LocationSearchError("Nearby healthcare search is temporarily unavailable.") from exc

        places = []
        for item in elements:
            tags = item.get("tags", {})
            point = item if "lat" in item and "lon" in item else item.get("center", {})
            if "lat" not in point or "lon" not in point:
                continue
            place_lat, place_lon = float(point["lat"]), float(point["lon"])
            places.append(
                {
                    "name": tags.get("name", "Unnamed healthcare facility"),
                    "type": tags.get("amenity", "healthcare"),
                    "address": ", ".join(
                        part for part in (
                            tags.get("addr:street"),
                            tags.get("addr:city"),
                            tags.get("addr:postcode"),
                        ) if part
                    ) or None,
                    "latitude": place_lat,
                    "longitude": place_lon,
                    "distance_km": round(self._distance_km(latitude, longitude, place_lat, place_lon), 2),
                    "map_url": f"https://www.openstreetmap.org/?mlat={place_lat}&mlon={place_lon}#map=17/{place_lat}/{place_lon}",
                    "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={place_lat}%2C{place_lon}",
                    "source": "OpenStreetMap",
                }
            )
        return sorted(places, key=lambda place: place["distance_km"])[:20]
