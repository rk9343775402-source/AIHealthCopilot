from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app

client = TestClient(app)


def register_user(payload):
    response = client.post(
        "/api/auth/register",
        json={
            **payload,
            "password": "fictional-test-password-123",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Personal Health Copilot" in response.json()["app"]


def test_cors_allows_production_frontend_and_local_development_origin():
    test_settings = Settings(database_url="sqlite://", _env_file=None)
    cors_app = FastAPI()
    cors_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in test_settings.allowed_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_client = TestClient(cors_app)

    for origin in (
        "https://aihealthcopilot.onrender.com",
        "http://localhost:5173",
    ):
        response = test_client.options(
            "/cors-probe",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_app_cors_handles_preflight_and_unauthenticated_api_response():
    origin = "https://aihealthcopilot.onrender.com"
    preflight = client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-credentials"] == "true"
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "content-type" in preflight.headers["access-control-allow-headers"].lower()

    unauthenticated = client.get("/api/auth/me", headers={"Origin": origin})
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["access-control-allow-origin"] == origin
    assert unauthenticated.headers["access-control-allow-credentials"] == "true"


def test_cors_headers_wrap_unhandled_api_errors():
    origin = "https://aihealthcopilot.onrender.com"

    async def fail():
        raise RuntimeError("synthetic CORS test failure")

    app.app.add_api_route("/cors-test-error", fail, methods=["GET"])
    route = app.app.router.routes[-1]
    try:
        with TestClient(app, raise_server_exceptions=False) as error_client:
            response = error_client.get(
                "/cors-test-error",
                headers={"Origin": origin},
            )
        assert response.status_code == 500
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
    finally:
        app.app.router.routes.remove(route)


def test_create_user_and_profile():
    payload = {"name": "Test User", "email": "test@example.com", "language": "en"}
    created = register_user(payload)
    user_id = created["id"]

    profile = client.get(f"/api/health-profile/{user_id}")
    assert profile.status_code == 200
    assert profile.json()["user"]["name"] == "Test User"


def test_lab_and_health_chat():
    user = register_user({"name": "Chat User", "email": "chat@example.com"})
    client.post(
        "/api/lab-results",
        json={
            "user_id": user["id"],
            "test_name": "Hemoglobin",
            "value": 12.4,
            "unit": "g/dL",
            "reference_range": "12.0-15.5",
            "status": "normal",
        },
    )

    chat = client.post(
        "/api/health-chat",
        json={"user_id": user["id"], "question": "What was my hemoglobin value?"},
    )
    assert chat.status_code == 200
    assert "answer" in chat.json()


def test_fhir_endpoint():
    user = register_user({"name": "FHIR User", "email": "fhir@example.com"})
    response = client.get(f"/api/fhir/patient/{user['id']}")
    assert response.status_code == 200
    assert response.json()["resourceType"] == "Patient"


def test_abdm_mock():
    user = register_user({"name": "ABDM User", "email": "abdm@example.com"})
    response = client.get(f"/api/abdm/mock/{user['id']}")
    assert response.status_code == 200
    assert "ABDM / ABHA MOCK DEMO" in response.json()["label"]
    assert response.json()["consent_status"] == "not_requested"
