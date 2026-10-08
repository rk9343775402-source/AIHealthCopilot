from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import (
    AnimalBite,
    Diagnosis,
    DoctorVisit,
    EmergencyEvent,
    Injury,
    LabResult,
    MedicalDocument,
    Medicine,
    User,
    Wellbeing,
)

router = APIRouter(prefix="/api", tags=["health-profile"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health-profile/{user_id}")
def health_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "language": user.language,
        },
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "document_type": document.document_type,
                "file_name": document.file_name,
                "mime_type": document.mime_type,
                "status": document.status,
                "source_date": document.source_date,
                "extracted_summary": document.extracted_summary,
                "explanation": document.explanation,
                "abnormal_values": document.abnormal_values,
                "created_at": document.created_at,
            }
            for document in db.query(MedicalDocument).filter(MedicalDocument.user_id == user_id).all()
        ],
        "lab_results": db.query(LabResult).filter(LabResult.user_id == user_id).all(),
        "medicines": db.query(Medicine).filter(Medicine.user_id == user_id).all(),
        "diagnoses": db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all(),
        "injuries": db.query(Injury).filter(Injury.user_id == user_id).all(),
        "animal_bites": db.query(AnimalBite).filter(AnimalBite.user_id == user_id).all(),
        "emergency_events": db.query(EmergencyEvent).filter(EmergencyEvent.user_id == user_id).all(),
        "doctor_visits": db.query(DoctorVisit).filter(DoctorVisit.user_id == user_id).all(),
        "wellbeing": db.query(Wellbeing).filter(Wellbeing.user_id == user_id).all(),
        "trusted_contacts": [
            {
                "id": contact.id,
                "name": contact.name,
                "phone": contact.phone,
                "contact_type": contact.contact_type,
            }
            for contact in user.trusted_contacts
        ],
    }
