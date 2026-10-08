from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Personal Health Copilot" in response.json()["app"]


def test_create_user_and_profile():
    payload = {"name": "Test User", "email": "test@example.com", "language": "en"}
    response = client.post("/api/users", json=payload)
    assert response.status_code == 200
    created = response.json()
    user_id = created["id"]

    profile = client.get(f"/api/health-profile/{user_id}")
    assert profile.status_code == 200
    assert profile.json()["user"]["name"] == "Test User"


def test_lab_and_health_chat():
    user = client.post("/api/users", json={"name": "Chat User", "email": "chat@example.com"}).json()
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
    user = client.post("/api/users", json={"name": "FHIR User", "email": "fhir@example.com"}).json()
    response = client.get(f"/api/fhir/patient/{user['id']}")
    assert response.status_code == 200
    assert response.json()["resourceType"] == "Patient"


def test_abdm_mock():
    user = client.post("/api/users", json={"name": "ABDM User", "email": "abdm@example.com"}).json()
    response = client.get(f"/api/abdm/mock/{user['id']}")
    assert response.status_code == 200
    assert "ABDM / ABHA MOCK DEMO" in response.json()["label"]
    assert response.json()["consent_status"] == "not_requested"
