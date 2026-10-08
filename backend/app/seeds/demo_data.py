from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.health import (
    AnimalBite,
    Diagnosis,
    DoctorVisit,
    EmergencyEvent,
    Injury,
    LabResult,
    MedicalDocument,
    Medicine,
    TrustedContact,
    User,
    Wellbeing,
)


def seed_demo_data(db: Session):
    if db.query(User).first():
        return

    user = User(
        id=1,
        name="Aarav Sharma",
        email="aarav@example.com",
        phone="+91 98765 43210",
        age=32,
        gender="male",
        location="Bengaluru",
        language="en",
    )
    db.add(user)
    db.flush()

    document = MedicalDocument(
        user_id=user.id,
        title="CBC Report",
        document_type="laboratory report",
        file_name="cbc_report.pdf",
        storage_path="/tmp/demo/cbc_report.pdf",
        mime_type="application/pdf",
        status="processed",
        source_date=date(2026, 9, 12),
        ocr_text="Hemoglobin 12.4 g/dL\nLDL 170 mg/dL\nReference range: LDL <130 mg/dL\nHemoglobin reference range 12.0-15.5 g/dL",
        extracted_summary="This report includes hemoglobin and LDL cholesterol values.",
        explanation="Your LDL cholesterol is higher than the reference range shown in this report.",
        abnormal_values="LDL Cholesterol: 170 mg/dL (above reference range)",
    )
    db.add(document)

    db.add(
        LabResult(
            user_id=user.id,
            source_document_id=document.id,
            test_name="Hemoglobin",
            value=12.4,
            unit="g/dL",
            reference_range="12.0-15.5",
            status="normal",
            test_date=date(2026, 9, 12),
        )
    )
    db.add(
        LabResult(
            user_id=user.id,
            source_document_id=document.id,
            test_name="LDL Cholesterol",
            value=170,
            unit="mg/dL",
            reference_range="<130",
            status="high",
            test_date=date(2026, 9, 12),
        )
    )

    db.add(
        Medicine(
            user_id=user.id,
            name="Atorvastatin",
            strength="10 mg",
            form="Tablet",
            manufacturer="Generic Pharma",
            dosage="1 tablet",
            frequency="Once daily",
            duration="30 days",
            notes="For cholesterol support",
            start_date=date(2026, 9, 1),
        )
    )

    db.add(
        Diagnosis(
            user_id=user.id,
            diagnosis_name="Mild hyperlipidemia",
            notes="Elevation noted in LDL cholesterol values.",
            doctor_name="Dr. Meena S",
            diagnosed_date=date(2026, 9, 11),
        )
    )

    db.add(
        Injury(
            user_id=user.id,
            body_location="Right forearm",
            description="Minor skin abrasion after a fall.",
            visible_findings="Small superficial abrasion; mild tenderness.",
            urgency="LOW CONCERN",
            first_aid="Clean gently with running water and cover with a clean dressing.",
            warning_signs="Increasing redness, swelling, fever, or severe pain.",
        )
    )

    db.add(
        AnimalBite(
            user_id=user.id,
            animal_type="dog",
            body_location="Left leg",
            description="Minor scratch after a dog interaction near a park.",
            urgency="LOW CONCERN",
            first_aid="Wash with soap and water and seek a clinician if the wound is deep or unusual.",
            rabies_awareness="Rabies risk must be evaluated by a healthcare professional when there is relevant exposure.",
        )
    )

    db.add(
        EmergencyEvent(
            user_id=user.id,
            event_type="first_aid_training",
            description="Completed a basic first-aid refresher.",
            location="Bengaluru",
            severity="LOW",
        )
    )

    db.add(
        DoctorVisit(
            user_id=user.id,
            doctor_name="Dr. Meena S",
            reason="Routine health review",
            summary="Discussed cholesterol trend and medicine plan.",
            visit_date=date(2026, 9, 11),
        )
    )

    db.add(
        Wellbeing(
            user_id=user.id,
            mood="Calm",
            stress_level=3,
            message="Felt okay overall and maintained a regular routine.",
            entry_date=date(2026, 9, 13),
        )
    )

    db.add(
        TrustedContact(
            user_id=user.id,
            name="Priya Sharma",
            phone="+91 90000 11111",
            contact_type="Spouse",
        )
    )

    db.commit()
