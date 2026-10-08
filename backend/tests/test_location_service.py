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


def test_nearby_care_endpoint_keeps_existing_502_response(monkeypatch):
    async def fail_lookup(*_args, **_kwargs):
        raise LocationSearchError("Nearby healthcare search is temporarily unavailable.")

    monkeypatch.setattr(emergency.LocationService, "nearby_care", fail_lookup)
    response = TestClient(app).get(
        "/api/nearby-care?latitude=37.7749&longitude=-122.4194"
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Nearby healthcare search is temporarily unavailable."
