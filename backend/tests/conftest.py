import os


def pytest_sessionstart(session):
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["DEMO_MODE"] = "false"
    os.environ["AUTH_SECRET_KEY"] = "test-only-secret-key-for-authentication-suite"
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app):
        pass
