from __future__ import annotations

import asyncio
import socket
from collections.abc import Iterable
from urllib.parse import urlsplit

import httpx

from app.services.location_service import LocationService

MIRROR_URL = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
TEST_QUERY = "[out:json];out count;"
TIMEOUT_SECONDS = 10.0


def _exception_errno(error: BaseException) -> int | None:
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))

        cause_errno = getattr(current, "errno", None)
        if isinstance(cause_errno, int) and not isinstance(cause_errno, bool):
            return cause_errno

        pending.extend(
            cause
            for cause in (current.__cause__, current.__context__)
            if cause is not None
        )
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
    return None


def _dns_result(hostname: str) -> tuple[str, BaseException | None]:
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        return "resolution_failed", exc
    return ("resolved", None) if addresses else ("no_addresses", None)


async def _probe(endpoint: str) -> None:
    hostname = urlsplit(endpoint).hostname
    if hostname is None:
        raise ValueError("Diagnostic endpoint must include a hostname.")

    dns_result, dns_error = _dns_result(hostname)
    if dns_error is not None or dns_result != "resolved":
        _log_result(
            hostname,
            dns_result,
            "not_attempted",
            None,
            dns_error,
        )
        return

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": "AIHealthCopilot/1.0 connectivity-diagnostic"},
        ) as client:
            response = await client.post(endpoint, data={"data": TEST_QUERY})
    except (httpx.HTTPError, OSError) as exc:
        _log_result(hostname, dns_result, "request_failed", None, exc)
        return

    _log_result(hostname, dns_result, "response_received", response.status_code, None)


def _log_result(
    hostname: str,
    dns_result: str,
    connection_outcome: str,
    http_status: int | None,
    error: BaseException | None,
) -> None:
    exception_class = type(error).__name__ if error is not None else "unavailable"
    error_number = _exception_errno(error) if error is not None else None
    print(
        "overpass_diagnostic "
        f"endpoint_host={hostname} "
        f"dns_result={dns_result} "
        f"connection_outcome={connection_outcome} "
        f"http_status={http_status if http_status is not None else 'unavailable'} "
        f"exception_class={exception_class} "
        f"errno={error_number if error_number is not None else 'unavailable'}"
    )


async def run_diagnostic(endpoints: Iterable[str] | None = None) -> None:
    for endpoint in endpoints or (LocationService.OVERPASS_URL, MIRROR_URL):
        await _probe(endpoint)


def main() -> None:
    asyncio.run(run_diagnostic())


if __name__ == "__main__":
    main()
