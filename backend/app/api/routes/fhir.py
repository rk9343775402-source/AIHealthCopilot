from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import LabResult, User
from app.services.fhir_service import FHIRService

router = APIRouter(prefix="/api/fhir", tags=["fhir"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/patient/{user_id}")
def patient_fhir(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return FHIRService.patient_to_fhir({
        "id": user.id,
        "name": user.name,
        "gender": user.gender,
        "phone": user.phone,
        "location": user.location,
        "language": user.language,
    })


@router.get("/observations/{user_id}")
def observations_fhir(user_id: int, db: Session = Depends(get_db)):
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    results = db.query(LabResult).filter(LabResult.user_id == user_id).all()
    return FHIRService.observations_to_fhir([{
        "id": item.id,
        "test_name": item.test_name,
        "value": item.value,
        "unit": item.unit,
        "reference_range": item.reference_range,
        "test_date": item.test_date,
        "user_id": item.user_id,
    } for item in results])


@router.get("/bundle/{user_id}")
def fhir_bundle(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    results = db.query(LabResult).filter(LabResult.user_id == user_id).all()
    return FHIRService.patient_bundle(
        {
            "id": user.id,
            "name": user.name,
            "gender": user.gender,
            "phone": user.phone,
            "location": user.location,
            "language": user.language,
        },
        [
            {
                "id": item.id,
                "user_id": item.user_id,
                "test_name": item.test_name,
                "value": item.value,
                "unit": item.unit,
                "reference_range": item.reference_range,
                "test_date": item.test_date,
            }
            for item in results
        ],
    )
