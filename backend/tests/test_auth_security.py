import re
from uuid import uuid4

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.routes import auth as auth_routes
from app.database.base import Base
from app.database.session import _TENANT_MODELS
from app.main import app, fastapi_app


PASSWORD_A = "fictional-user-a-password-123"
PASSWORD_B = "fictional-user-b-password-456"


def register(client: TestClient, name: str, password: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": f"{name.casefold().replace(' ', '.')}-{uuid4().hex}@example.com",
            "password": password,
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def test_all_private_api_routes_reject_unauthenticated_requests():
    public_paths = {"/api/auth/register", "/api/auth/login"}
    with TestClient(app) as client:
        for route in fastapi_app.routes:
            if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
                continue
            if route.path in public_paths:
                continue
            path = re.sub(r"\{[^}]+\}", "1", route.path)
            for method in route.methods - {"OPTIONS", "HEAD"}:
                response = client.request(method, path)
                assert response.status_code == 401, f"{method} {route.path} was not protected"


def test_every_user_owned_orm_model_is_tenant_scoped():
    scoped_models = set(_TENANT_MODELS)
    user_owned_models = {
        mapper.class_
        for mapper in Base.registry.mappers
        if "user_id" in mapper.attrs
    }
    assert user_owned_models
    assert user_owned_models <= scoped_models


def test_registration_and_login_require_a_32_byte_auth_secret(monkeypatch):
    for secret in ("", "x" * 31):
        monkeypatch.setattr(auth_routes.settings, "auth_secret_key", secret)
        with TestClient(app) as client:
            register_response = client.post(
                "/api/auth/register",
                json={
                    "name": "Fictional Configuration Test",
                    "email": f"missing-secret-{uuid4().hex}@example.com",
                    "password": PASSWORD_A,
                },
            )
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "fictional@example.com",
                    "password": PASSWORD_A,
                },
            )

        for response in (register_response, login_response):
            assert response.status_code == 503
            assert response.json()["detail"] == "Authentication is not configured."


def test_registration_login_and_profile_responses_never_return_credentials():
    with TestClient(app) as client:
        password = "fictional-auth-test-password-789"
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Fictional Account",
                "email": f"auth-{uuid4().hex}@example.com",
                "password": password,
            },
        )
        assert response.status_code == 201
        assert response.cookies.get("carecompass_session")
        assert response.headers["set-cookie"].lower().find("httponly") >= 0
        assert response.headers["set-cookie"].lower().find("samesite=lax") >= 0
        assert "password_hash" not in response.text
        assert password not in response.text
        assert "token" not in response.json()

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert "password_hash" not in me.text
        assert password not in me.text

        logout = client.post("/api/auth/logout")
        assert logout.status_code == 204
        assert client.get("/api/auth/me").status_code == 401

        login = client.post(
            "/api/auth/login",
            json={"email": response.json()["user"]["email"], "password": password},
        )
        assert login.status_code == 200
        assert "password_hash" not in login.text
        assert password not in login.text
        assert "token" not in login.json()


def test_production_cookie_supports_cross_origin_session_validation(monkeypatch):
    monkeypatch.setattr(auth_routes.settings, "app_env", "production")
    origin = "https://aihealthcopilot.onrender.com"
    with TestClient(
        app,
        base_url="https://ai-health-copilot-backend.onrender.com",
    ) as client:
        registration = client.post(
            "/api/auth/register",
            headers={"Origin": origin},
            json={
                "name": "Fictional Production Cookie Test",
                "email": f"cookie-{uuid4().hex}@example.com",
                "password": "fictional-production-cookie-password",
            },
        )
        assert registration.status_code == 201
        cookie_header = registration.headers["set-cookie"].lower()
        assert "httponly" in cookie_header
        assert "secure" in cookie_header
        assert "samesite=none" in cookie_header
        assert "path=/" in cookie_header
        assert f"max-age={auth_routes.settings.auth_token_expire_minutes * 60}" in cookie_header

        session = client.get("/api/auth/me", headers={"Origin": origin})
        assert session.status_code == 200
        assert session.json()["user"]["email"] == registration.json()["user"]["email"]

        logout = client.post("/api/auth/logout", headers={"Origin": origin})
        assert logout.status_code == 204
        assert client.get("/api/auth/me", headers={"Origin": origin}).status_code == 401


def test_two_accounts_cannot_read_or_modify_each_others_records():
    with TestClient(app) as client_a, TestClient(app) as client_b:
        user_a = register(client_a, "Fictional User A", PASSWORD_A)
        user_b = register(client_b, "Fictional User B", PASSWORD_B)

        created = client_a.post(
            "/api/diagnoses",
            json={
                "user_id": user_a["id"],
                "diagnosis_name": "Fictional test diagnosis",
                "notes": "Not a real health record",
            },
        )
        assert created.status_code == 201
        diagnosis_id = created.json()["id"]

        assert client_b.get(f"/api/health-profile/{user_a['id']}").status_code == 404
        assert client_b.get(f"/api/diagnoses/{user_a['id']}").status_code == 404
        assert client_b.delete(f"/api/diagnoses/{diagnosis_id}").status_code == 404
        assert client_b.post(
            "/api/lab-results",
            json={
                "user_id": user_a["id"],
                "test_name": "Fictional unauthorized record",
                "value": 1.0,
            },
        ).status_code == 404

        own_records = client_a.get(f"/api/diagnoses/{user_a['id']}")
        assert own_records.status_code == 200
        assert [item["id"] for item in own_records.json()["items"]] == [diagnosis_id]
        assert client_b.get(f"/api/health-profile/{user_b['id']}").status_code == 200
