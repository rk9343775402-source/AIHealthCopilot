import errno
import socket
import ssl

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import emergency
from app.main import app
from app.services.location_service import LocationSearchError, LocationService


class FailingAsyncClient:
    def __init__(self, error):
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, *_args, **_kwargs):
        raise self.error


@pytest.mark.asyncio
async def test_overpass_http_failure_logs_status_without_response_body(monkeypatch, caplog):
    request = httpx.Request("POST", LocationService.OVERPASS_URL)
    response = httpx.Response(
        503,
        request=request,
        text="private-token 37.7749,-122.4194 upstream details",
    )
    error = httpx.HTTPStatusError(
        "upstream failure",
        request=request,
        response=response,
    )
    monkeypatch.setattr(
        "app.services.location_service.httpx.AsyncClient",
        lambda **_kwargs: FailingAsyncClient(error),
    )

    with pytest.raises(LocationSearchError):
        await LocationService().nearby_care(37.7749, -122.4194)

    assert "exception_type=HTTPStatusError" in caplog.text
    assert "upstream_status=503" in caplog.text
    assert "error=Service Unavailable" in caplog.text
    assert "private-token" not in caplog.text
    assert "37.7749" not in caplog.text
    assert "-122.4194" not in caplog.text
    assert "upstream details" not in caplog.text


@pytest.mark.asyncio
async def test_overpass_timeout_logs_safe_failure_category(monkeypatch, caplog):
    error = httpx.ReadTimeout("request failed")
    monkeypatch.setattr(
        "app.services.location_service.httpx.AsyncClient",
        lambda **_kwargs: FailingAsyncClient(error),
    )

    with pytest.raises(LocationSearchError):
        await LocationService().nearby_care(37.7749, -122.4194)

    assert "exception_type=ReadTimeout" in caplog.text
    assert "upstream_status=unavailable" in caplog.text
    assert "error=upstream request timed out" in caplog.text


@pytest.mark.parametrize(
    ("cause", "cause_type", "cause_errno", "phase", "category"),
    [
        (
            socket.gaierror(socket.EAI_NONAME, "sensitive resolver detail"),
            "gaierror",
            socket.EAI_NONAME,
            "dns",
            "dns_resolution_failure",
        ),
        (
            ConnectionRefusedError(errno.ECONNREFUSED, "sensitive socket detail"),
            "ConnectionRefusedError",
            errno.ECONNREFUSED,
            "tcp",
            "tcp_connection_refused",
        ),
        (
            TimeoutError(errno.ETIMEDOUT, "sensitive timeout detail"),
            "TimeoutError",
            errno.ETIMEDOUT,
            "tcp",
            "tcp_connection_timeout",
        ),
        (
            ssl.SSLError("sensitive TLS detail"),
            "SSLError",
            None,
            "tls",
            "tls_connection_failure",
        ),
        (
            httpx.ProxyError("sensitive proxy detail"),
            "ProxyError",
            None,
            "proxy",
            "proxy_connection_failure",
        ),
        (
            RuntimeError("sensitive connection detail"),
            "RuntimeError",
            None,
            "connect",
            "other_connection_failure",
        ),
    ],
)
@pytest.mark.asyncio
async def test_connect_error_logs_safe_nested_cause_classification(
    monkeypatch, caplog, cause, cause_type, cause_errno, phase, category
):
    request = httpx.Request("POST", LocationService.OVERPASS_URL)
    error = httpx.ConnectError(
        "sensitive URL, credentials, and location details",
        request=request,
    )
    error.__cause__ = cause
    monkeypatch.setattr(
        "app.services.location_service.httpx.AsyncClient",
        lambda **_kwargs: FailingAsyncClient(error),
    )

    with pytest.raises(LocationSearchError):
        await LocationService().nearby_care(37.7749, -122.4194)

    assert "exception_type=ConnectError" in caplog.text
    assert f"cause_type={cause_type}" in caplog.text
    assert f"cause_errno={cause_errno if cause_errno is not None else 'unavailable'}" in caplog.text
    assert f"connection_phase={phase}" in caplog.text
    assert "upstream_status=unavailable" in caplog.text
    assert f"error={category}" in caplog.text
    assert "sensitive" not in caplog.text
    assert "37.7749" not in caplog.text
    assert "-122.4194" not in caplog.text


@pytest.mark.parametrize(
    ("nested_cause", "cause_type", "cause_errno", "phase", "category"),
    [
        (
            socket.gaierror(socket.EAI_NONAME, "sensitive DNS text"),
            "gaierror",
            socket.EAI_NONAME,
            "dns",
            "dns_resolution_failure",
        ),
        (
            ConnectionRefusedError(errno.ECONNREFUSED, "sensitive TCP text"),
            "ConnectionRefusedError",
            errno.ECONNREFUSED,
            "tcp",
            "tcp_connection_refused",
        ),
        (
            ssl.SSLError("sensitive TLS text"),
            "SSLError",
            None,
            "tls",
            "tls_connection_failure",
        ),
    ],
)
@pytest.mark.asyncio
async def test_connect_error_recursively_classifies_exception_groups(
    monkeypatch,
    caplog,
    nested_cause,
    cause_type,
    cause_errno,
    phase,
    category,
):
    request = httpx.Request("POST", LocationService.OVERPASS_URL)
    nested_connection_error = httpx.ConnectError(
        "sensitive nested connection text",
        request=request,
    )
    nested_connection_error.__cause__ = nested_cause
    nested_connection_error.__context__ = RuntimeError("sensitive context text")
    nested_group = ExceptionGroup(
        "sensitive nested group text",
        [nested_connection_error],
    )
    cause_group = ExceptionGroup("sensitive outer group text", [nested_group])
    error = httpx.ConnectError(
        "sensitive URL, credentials, and location details",
        request=request,
    )
    error.__cause__ = cause_group
    monkeypatch.setattr(
        "app.services.location_service.httpx.AsyncClient",
        lambda **_kwargs: FailingAsyncClient(error),
    )

    with pytest.raises(LocationSearchError):
        await LocationService().nearby_care(37.7749, -122.4194)

    assert "exception_type=ConnectError" in caplog.text
    assert f"cause_type={cause_type}" in caplog.text
    assert "cause_types=ExceptionGroup,ConnectError" in caplog.text
    assert "RuntimeError" in caplog.text
    assert f"cause_errno={cause_errno if cause_errno is not None else 'unavailable'}" in caplog.text
    assert f"connection_phase={phase}" in caplog.text
    assert f"error={category}" in caplog.text
    assert "sensitive" not in caplog.text
    assert "37.7749" not in caplog.text
    assert "-122.4194" not in caplog.text


def test_nearby_care_endpoint_keeps_existing_502_response(monkeypatch):
    async def fail_lookup(*_args, **_kwargs):
        raise LocationSearchError("Nearby healthcare search is temporarily unavailable.")

    monkeypatch.setattr(emergency.LocationService, "nearby_care", fail_lookup)
    response = TestClient(app).get(
        "/api/nearby-care?latitude=37.7749&longitude=-122.4194"
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Nearby healthcare search is temporarily unavailable."
