from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import LabResult, MedicalDocument, Medicine, User

router = APIRouter(prefix="/api/abdm", tags=["abdm"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/mock/{user_id}")
def mock_abdm(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "label": "ABDM / ABHA MOCK DEMO",
        "user_id": user_id,
        "status": "mock-integration",
        "message": "This is a local integration preview. No ABDM/ABHA connection or data transfer occurred.",
        "consent_status": "not_requested",
        "patient": {"id": user_id, "name": user.name},
        "available_record_counts": {
            "medical_documents": db.query(MedicalDocument).filter(MedicalDocument.user_id == user_id).count(),
            "lab_results": db.query(LabResult).filter(LabResult.user_id == user_id).count(),
            "medicines": db.query(Medicine).filter(Medicine.user_id == user_id).count(),
        },
    }
