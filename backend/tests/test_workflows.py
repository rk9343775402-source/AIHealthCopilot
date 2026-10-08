import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.session import _normalize_database_url
from app.main import app
from app.services.ocr_service import OCRService

client = TestClient(app)


def create_user(name="Workflow User"):
    response = client.post("/api/users", json={"name": name})
    assert response.status_code == 200
    return response.json()


def test_ocr_extracts_values_and_flags_only_explicit_reference_ranges():
    candidates = OCRService.extract_lab_candidates(
        "Hemoglobin: 11.2 g/dL (12.0-16.0)\n"
        "LDL: 142 mg/dL (<130)\n"
        "Glucose: 95 mg/dL"
    )
    assert [(item["name"], item["status"]) for item in candidates] == [
        ("Hemoglobin", "low"),
        ("LDL Cholesterol", "high"),
        ("Glucose", "unknown"),
    ]


def test_ocr_extracts_multiline_table_lab_rows_and_normalizes_mojibake():
    report_text = (
        "Test\n"
        "Result\n"
        "Reference Range\n"
        "Unit\n"
        "Hemoglobin\n"
        "13.8\n"
        "13.0â\u0080\u009317.0\n"
        "g/dL\n"
        "WBC Count\n"
        "7,200\n"
        "4,000â\u0080\u009311,000\n"
        "/µL\n"
        "Fasting Glucose\n"
        "108\n"
        "70â\u0080\u009399\n"
        "mg/dL\n"
        "Vitamin B12\n"
        "185\n"
        "200â\u0080\u0093900\n"
        "pg/mL\n"
        "Vitamin D\n"
        "18\n"
        "30â\u0080\u0093100\n"
        "ng/mL\n"
        "Total Cholesterol\n"
        "178\n"
        "<200\n"
        "mg/dL"
    )

    processed = OCRService.process_document(report_text)
    candidates = processed["detected_tests"]
    by_name = {item["name"]: item for item in candidates}

    assert len(candidates) == 6
    assert "found 6 possible laboratory value(s)" in processed["summary"]
    assert (by_name["Hemoglobin"]["value"], by_name["Hemoglobin"]["reference_range"]) == (
        13.8,
        "13.0-17.0",
    )
    assert by_name["Hemoglobin"]["unit"] == "g/dL"
    assert (by_name["White Blood Cell Count"]["value"], by_name["White Blood Cell Count"]["unit"]) == (
        7200,
        "/µL",
    )
    assert by_name["White Blood Cell Count"]["reference_range"] == "4,000-11,000"
    assert (
        by_name["Glucose"]["value"],
        by_name["Glucose"]["reference_range"],
        by_name["Glucose"]["unit"],
        by_name["Glucose"]["status"],
    ) == (108, "70-99", "mg/dL", "high")
    assert (
        by_name["Vitamin B12"]["value"],
        by_name["Vitamin B12"]["reference_range"],
        by_name["Vitamin B12"]["unit"],
        by_name["Vitamin B12"]["status"],
    ) == (185, "200-900", "pg/mL", "low")
    assert (
        by_name["Vitamin D"]["value"],
        by_name["Vitamin D"]["reference_range"],
        by_name["Vitamin D"]["unit"],
        by_name["Vitamin D"]["status"],
    ) == (18, "30-100", "ng/mL", "low")
    assert (
        by_name["Cholesterol"]["value"],
        by_name["Cholesterol"]["reference_range"],
        by_name["Cholesterol"]["unit"],
        by_name["Cholesterol"]["status"],
    ) == (178, "<200", "mg/dL", "normal")
    assert OCRService.normalize_text("1â\u0080\u00942") == "1-2"
    assert OCRService.normalize_text("1â€“2") == "1-2"
    assert OCRService.normalize_text("1â€”2") == "1-2"


def test_document_analysis_requires_explicit_result_confirmation():
    user = create_user()
    document = client.post(
        "/api/medical-documents",
        json={
            "user_id": user["id"],
            "title": "Lab report",
            "document_type": "laboratory",
            "ocr_text": "Hemoglobin: 11.2 g/dL (12.0-16.0)\nLDL: 142 mg/dL (<130)",
        },
    )
    assert document.status_code == 200
    document_id = document.json()["id"]

    analyzed = client.post(f"/api/medical-documents/{document_id}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["review_required"] is True
    assert [item["status"] for item in analyzed.json()["processing"]["detected_tests"]] == ["low", "high"]
    assert client.get(f"/api/lab-results/{user['id']}").json()["items"] == []

    confirmed = client.post(
        f"/api/medical-documents/{document_id}/confirm",
        json={"user_id": user["id"], "candidate_indices": [0, 1]},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    results = client.get(f"/api/lab-results/{user['id']}").json()["items"]
    assert [item["test_name"] for item in results] == ["Hemoglobin", "LDL Cholesterol"]
    assert client.post(
        f"/api/medical-documents/{document_id}/confirm",
        json={"user_id": user["id"], "candidate_indices": [0]},
    ).status_code == 409


def test_uploaded_pdf_analysis_extracts_abnormal_values_from_ocr_style_lab_rows(
    tmp_path, monkeypatch
):
    from io import BytesIO

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    from app.core.config import settings
    from app.services.ai_service import AIService

    user = create_user()
    report_text = (
        "Hemoglobin 13.8 13.0\u201317.0 g/dL\n"
        "WBC Count 7,200 4,000\u201311,000 /\u00b5L\n"
        "Fasting Glucose 108 70\u201399 mg/dL\n"
        "Vitamin B12 185 200\u2013900 pg/mL\n"
        "Vitamin D 18 30\u2013100 ng/mL\n"
        "Total Cholesterol 178 <200 mg/dL"
    )
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    def pdf_literal(value):
        return (
            value.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .encode("cp1252")
        )

    pdf = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = (
        b"BT /F1 10 Tf 50 750 Td "
        + b" 0 -14 Td ".join(
            b"(" + pdf_literal(line) + b") Tj" for line in report_text.splitlines()
        )
        + b" ET"
    )
    content_stream = DecodedStreamObject()
    content_stream.set_data(content)
    page[NameObject("/Contents")] = writer._add_object(content_stream)
    writer.write(pdf)

    async def local_explanation(_service, _text):
        return {
            "summary": "AI explanation is unavailable in this test.",
            "ai_status": "unavailable",
        }

    monkeypatch.setattr(AIService, "summarize_document", local_explanation)

    uploaded = client.post(
        "/api/medical-documents/upload",
        data={
            "user_id": str(user["id"]),
            "title": "Lab report",
            "document_type": "laboratory",
        },
        files={"file": ("report.pdf", pdf.getvalue(), "application/pdf")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["ocr_text"] == report_text
    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != "report.pdf"

    analyzed = client.post(f"/api/medical-documents/{uploaded.json()['id']}/analyze")

    assert analyzed.status_code == 200
    response = analyzed.json()
    assert [
        (item["name"], item["value"], item["reference_range"], item["status"])
        for item in response["processing"]["detected_tests"]
    ] == [
        ("Hemoglobin", 13.8, "13.0\u201317.0", "normal"),
        ("White Blood Cell Count", 7200.0, "4,000\u201311,000", "normal"),
        ("Glucose", 108.0, "70\u201399", "high"),
        ("Vitamin B12", 185.0, "200\u2013900", "low"),
        ("Vitamin D", 18.0, "30\u2013100", "low"),
        ("Cholesterol", 178.0, "<200", "normal"),
    ]
    assert [
        (item["name"], item["status"])
        for item in response["abnormal_values"]
    ] == [
        ("Glucose", "high"),
        ("Vitamin B12", "low"),
        ("Vitamin D", "low"),
    ]
    assert response["processing"]["summary"].endswith("found 6 possible laboratory value(s). Please verify every extracted item against the original report.")
    assert response["explanation"]["ai_status"] == "unavailable"

    confirmed = client.post(
        response["confirmation_endpoint"],
        json={"user_id": user["id"], "candidate_indices": list(range(6))},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    saved_labs = client.get(f"/api/lab-results/{user['id']}").json()["items"]
    assert [(item["test_name"], item["value"], item["status"]) for item in saved_labs] == [
        ("Hemoglobin", 13.8, "normal"),
        ("White Blood Cell Count", 7200.0, "normal"),
        ("Glucose", 108.0, "high"),
        ("Vitamin B12", 185.0, "low"),
        ("Vitamin D", 18.0, "low"),
        ("Cholesterol", 178.0, "normal"),
    ]
    profile = client.get(f"/api/health-profile/{user['id']}").json()
    saved_document = profile["documents"][0]
    assert saved_document["status"] == "confirmed"
    assert json.loads(saved_document["abnormal_values"]) == response["abnormal_values"]
    timeline = client.get(f"/api/timeline/{user['id']}").json()["items"]
    assert {event["event_type"] for event in timeline} >= {
        "medical_document",
        "medical_document_confirmed",
    }

def test_unsafe_upload_content_is_rejected():
    user = create_user()
    response = client.post(
        "/api/medical-documents/upload",
        data={"user_id": str(user["id"]), "title": "Report", "document_type": "report"},
        files={"file": ("report.txt", b"not a medical document", "text/plain")},
    )
    assert response.status_code == 415


def test_valid_document_upload_is_stored_with_a_generated_name(tmp_path, monkeypatch):
    from io import BytesIO

    from pypdf import PdfWriter

    from app.core.config import settings

    user = create_user()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(pdf)
    monkeypatch.setattr(
        OCRService,
        "extract_text",
        staticmethod(lambda content, mime_type: ("Reviewed with clinician.", "pdf-text")),
    )

    response = client.post(
        "/api/medical-documents/upload",
        data={"user_id": str(user["id"]), "title": "Visit note", "document_type": "visit"},
        files={"file": ("visit.pdf", pdf.getvalue(), "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["file_name"] == "visit.pdf"
    assert "storage_path" not in response.json()
    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name != "visit.pdf"


def test_lab_trends_use_saved_values_only():
    user = create_user()
    for test_date, value in [("2026-01-01", 110), ("2026-02-01", 105)]:
        result = client.post(
            "/api/lab-results",
            json={
                "user_id": user["id"],
                "test_name": "Glucose",
                "value": value,
                "unit": "mg/dL",
                "reference_range": "70-100",
                "status": "high",
                "test_date": test_date,
            },
        )
        assert result.status_code == 200
    trend = client.get(f"/api/lab-results/{user['id']}/trends")
    assert trend.status_code == 200
    glucose = trend.json()["items"][0]
    assert glucose["direction"] == "decreased"
    assert glucose["change"] == -5
    assert [point["value"] for point in glucose["values"]] == [110, 105]


def test_health_chat_does_not_invent_unrecorded_information():
    user = create_user()
    response = client.post(
        "/api/health-chat",
        json={"user_id": user["id"], "question": "What is my blood type?"},
    )
    assert response.status_code == 200
    assert response.json()["evidence"] == []
    assert "couldn't find" in response.json()["answer"]


def test_health_chat_retrieves_lab_evidence_for_hindi_queries():
    user = create_user()
    result = client.post(
        "/api/lab-results",
        json={
            "user_id": user["id"],
            "test_name": "Hemoglobin",
            "value": 13.2,
            "unit": "g/dL",
            "test_date": "2026-01-01",
        },
    )
    assert result.status_code == 200
    response = client.post(
        "/api/health-chat",
        json={"user_id": user["id"], "question": "मेरी लैब रिपोर्ट क्या कहती है?", "response_language": "hi"},
    )
    assert response.status_code == 200
    assert response.json()["evidence"][0]["source_type"] == "lab_result"
    assert response.json()["evidence"][0]["value"] == 13.2


def test_health_profile_serializes_contacts_without_storage_paths():
    user = create_user()
    contact = client.post(
        "/api/trusted-contacts",
        json={"user_id": user["id"], "name": "Trusted person", "phone": "+15555550123"},
    )
    document = client.post(
        "/api/medical-documents",
        json={
            "user_id": user["id"],
            "title": "Visit note",
            "document_type": "visit",
            "ocr_text": "Reviewed with clinician.",
        },
    )
    assert contact.status_code == 201
    assert document.status_code == 200

    response = client.get(f"/api/health-profile/{user['id']}")
    assert response.status_code == 200
    profile = response.json()
    assert profile["trusted_contacts"][0]["name"] == "Trusted person"
    assert "storage_path" not in profile["documents"][0]


def test_crisis_terms_are_escalated_without_calling_ai():
    response = client.post(
        "/api/wellbeing/response",
        json={"message": "I want to end my life", "language": "en"},
    )
    assert response.status_code == 200
    assert response.json()["crisis_escalation"] is True
    assert "local emergency number" in response.json()["response"]


def test_trusted_contact_location_message_is_prepared_not_sent():
    user = create_user()
    contact = client.post(
        "/api/trusted-contacts",
        json={"user_id": user["id"], "name": "Trusted person", "phone": "+15555550123"},
    )
    assert contact.status_code == 201
    prepared = client.post(
        "/api/emergency/location-share/prepare",
        json={
            "user_id": user["id"],
            "contact_id": contact.json()["id"],
            "latitude": 37.7749,
            "longitude": -122.4194,
        },
    )
    assert prepared.status_code == 200
    assert prepared.json()["delivery_status"] == "not_sent"
    assert "37.774900,-122.419400" in prepared.json()["message"]


def test_database_url_must_be_configured(monkeypatch):
    import pytest
    from pydantic import ValidationError

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_postgresql_database_urls_use_psycopg3_driver():
    urls = [
        "postgres://user:password@localhost:5432/app",
        "postgresql://user:password@localhost:5432/app",
        "postgresql+psycopg://user:password@localhost:5432/app",
    ]
    normalized = [_normalize_database_url(value) for value in urls]

    assert [url.drivername for url in normalized] == [
        "postgresql+psycopg",
        "postgresql+psycopg",
        "postgresql+psycopg",
    ]


def test_unconfigured_image_recognition_does_not_guess_a_medicine():
    import base64
    from io import BytesIO

    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
    one_pixel_png = base64.b64encode(image_buffer.getvalue()).decode("ascii")
    response = client.post(
        "/api/medicines/recognize",
        json={"image_data_url": f"data:image/png;base64,{one_pixel_png}"},
    )
    assert response.status_code == 200
    assert response.json()["identified"] is False
    assert "name" not in response.json()
    assert response.json()["verified_by_user"] is False


def test_corrupt_image_is_rejected_before_recognition():
    response = client.post(
        "/api/medicines/recognize",
        json={"image_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="},
    )
    assert response.status_code == 422


def test_unconfigured_injury_image_review_is_explicitly_not_a_diagnosis():
    response = client.post(
        "/api/injuries/analyze",
        json={"description": "Small cut on my hand. It is bleeding."},
    )
    assert response.status_code == 200
    assert response.json()["diagnosis"] is None
    assert response.json()["wound_depth"] is None
    assert "not a diagnosis" in response.json()["safety_note"]
