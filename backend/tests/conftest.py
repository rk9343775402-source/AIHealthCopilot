import os


def pytest_sessionstart(session):
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["DEMO_MODE"] = "false"
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app):
        pass
