import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from app.core.config import settings
from app.database.base import Base
from app.database.session import SessionLocal
from app.main import app


def _test_database_url() -> str | None:
    configured = os.environ.get("TEST_DATABASE_URL")
    if configured:
        return configured
    local_config = Path(__file__).parents[1] / ".env.test"
    if local_config.exists():
        return dotenv_values(local_config).get("TEST_DATABASE_URL")
    return None


@pytest.fixture
def postgres_test_database():
    raw_url = _test_database_url()
    if not raw_url:
        pytest.skip("Set TEST_DATABASE_URL or configure backend/.env.test for PostgreSQL integration tests.")
    try:
        database_url = make_url(raw_url)
    except ArgumentError:
        pytest.fail("TEST_DATABASE_URL is invalid; its value is intentionally not displayed.", pytrace=False)

    if database_url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        pytest.fail("PostgreSQL integration tests require a PostgreSQL URL.", pytrace=False)
    if database_url.database != "ai_health_copilot_test":
        pytest.fail(
            "Refusing to run integration tests unless the database is named ai_health_copilot_test.",
            pytrace=False,
        )
    if len(settings.auth_secret_key.encode("utf-8")) < 32:
        pytest.fail("The test process does not have the required test authentication key.", pytrace=False)

    test_engine = create_engine(
        database_url.set(drivername="postgresql+psycopg"),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        with test_engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    except SQLAlchemyError:
        test_engine.dispose()
        pytest.fail("Could not connect to the dedicated PostgreSQL test database; credentials were withheld.", pytrace=False)

    previous_bind = SessionLocal.kw.get("bind")
    try:
        Base.metadata.create_all(bind=test_engine)
        SessionLocal.configure(bind=test_engine)
        yield
    finally:
        SessionLocal.configure(bind=previous_bind)
        test_engine.dispose()


@pytest.mark.postgres_integration
def test_postgres_auth_sessions_and_tenant_record_isolation(postgres_test_database):
    email_a = f"fictional-a-{uuid4().hex}@example.com"
    email_b = f"fictional-b-{uuid4().hex}@example.com"
    password_a = "fictional-user-a-password-123"
    password_b = "fictional-user-b-password-456"

    with TestClient(app) as client_a, TestClient(app) as client_b:
        assert client_a.get("/api/auth/me").status_code == 401

        register_a = client_a.post(
            "/api/auth/register",
            json={"name": "Fictional User A", "email": email_a, "password": password_a},
        )
        register_b = client_b.post(
            "/api/auth/register",
            json={"name": "Fictional User B", "email": email_b, "password": password_b},
        )
        assert register_a.status_code == 201
        assert register_b.status_code == 201
        assert "password_hash" not in register_a.text
        assert password_a not in register_a.text
        assert register_a.headers["set-cookie"].lower().find("httponly") >= 0

        user_a = register_a.json()["user"]
        user_b = register_b.json()["user"]
        assert client_a.get("/api/auth/me").json()["user"]["id"] == user_a["id"]

        created = client_a.post(
            "/api/diagnoses",
            json={
                "user_id": user_a["id"],
                "diagnosis_name": "Fictional test record",
                "notes": "Synthetic integration-test data only.",
            },
        )
        assert created.status_code == 201
        record_id = created.json()["id"]

        assert client_a.get(f"/api/diagnoses/{user_a['id']}").json()["items"][0]["id"] == record_id
        assert client_b.get(f"/api/diagnoses/{user_a['id']}").status_code == 404
        assert client_b.delete(f"/api/diagnoses/{record_id}").status_code == 404
        assert client_b.post(
            "/api/diagnoses",
            json={
                "user_id": user_a["id"],
                "diagnosis_name": "Unauthorized fictional record",
            },
        ).status_code == 404
        assert client_b.get(f"/api/health-profile/{user_a['id']}").status_code == 404
        assert client_b.get(f"/api/health-profile/{user_b['id']}").status_code == 200

        expired_token = jwt.encode(
            {
                "sub": str(user_b["id"]),
                "iat": datetime.now(timezone.utc) - timedelta(minutes=5),
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            settings.auth_secret_key,
            algorithm="HS256",
        )
        client_b.cookies.set("carecompass_session", expired_token)
        assert client_b.get("/api/auth/me").status_code == 401

        client_b.cookies.clear()
        login = client_b.post("/api/auth/login", json={"email": email_b, "password": password_b})
        assert login.status_code == 200
        assert "password_hash" not in login.text
        assert password_b not in login.text
        assert client_b.get("/api/auth/me").status_code == 200

        logout = client_b.post("/api/auth/logout")
        assert logout.status_code == 204
        assert client_b.get("/api/auth/me").status_code == 401
