from __future__ import annotations

import errno
import logging
import math
import socket
import ssl
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LocationSearchError(RuntimeError):
    pass


def _connect_error_details(
    error: httpx.ConnectError,
) -> tuple[str | None, int | None, str, str]:
    causes: list[BaseException] = []
    cause = error.__cause__ or error.__context__
    while cause is not None and cause not in causes:
        causes.append(cause)
        cause = cause.__cause__ or cause.__context__

    cause_type = type(causes[-1]).__name__ if causes else None
    cause_errno = next(
        (
            candidate.errno
            for candidate in reversed(causes)
            if isinstance(getattr(candidate, "errno", None), int)
            and not isinstance(candidate.errno, bool)
        ),
        None,
    )
    cause_names = {type(candidate).__name__.casefold() for candidate in causes}

    if any("proxy" in name for name in cause_names):
        return cause_type, cause_errno, "proxy", "proxy_connection_failure"
    if any(isinstance(candidate, ssl.SSLError) for candidate in causes):
        return cause_type, cause_errno, "tls", "tls_connection_failure"
    if any(isinstance(candidate, socket.gaierror) for candidate in causes):
        return cause_type, cause_errno, "dns", "dns_resolution_failure"
    if any(
        isinstance(candidate, ConnectionRefusedError)
        or getattr(candidate, "errno", None) == errno.ECONNREFUSED
        for candidate in causes
    ):
        return cause_type, cause_errno, "tcp", "tcp_connection_refused"
    if any(
        isinstance(candidate, TimeoutError)
        or getattr(candidate, "errno", None) == errno.ETIMEDOUT
        for candidate in causes
    ):
        return cause_type, cause_errno, "tcp", "tcp_connection_timeout"
    if any(isinstance(candidate, OSError) for candidate in causes):
        return cause_type, cause_errno, "tcp", "tcp_connection_failure"
    return cause_type, cause_errno, "connect", "other_connection_failure"


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
            upstream_status = (
                exc.response.status_code
                if isinstance(exc, httpx.HTTPStatusError)
                else None
            )
            if isinstance(exc, httpx.HTTPStatusError):
                safe_error = exc.response.reason_phrase or "upstream HTTP error"
            elif isinstance(exc, httpx.TimeoutException):
                safe_error = "upstream request timed out"
            elif isinstance(exc, httpx.ConnectError):
                safe_error = "upstream connection failed"
            elif isinstance(exc, ValueError):
                safe_error = "upstream response JSON could not be decoded"
            else:
                safe_error = "upstream HTTP client error"
            if isinstance(exc, httpx.ConnectError):
                cause_type, cause_errno, connection_phase, safe_error = (
                    _connect_error_details(exc)
                )
                logger.warning(
                    "Nearby-care lookup failed: exception_type=%s cause_type=%s "
                    "cause_errno=%s connection_phase=%s upstream_status=%s error=%s",
                    type(exc).__name__,
                    cause_type or "unavailable",
                    cause_errno if cause_errno is not None else "unavailable",
                    connection_phase,
                    upstream_status if upstream_status is not None else "unavailable",
                    safe_error,
                )
            else:
                logger.warning(
                    "Nearby-care lookup failed: exception_type=%s upstream_status=%s error=%s",
                    type(exc).__name__,
                    upstream_status if upstream_status is not None else "unavailable",
                    safe_error,
                )
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
