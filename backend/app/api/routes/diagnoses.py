from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import Diagnosis, HealthTimeline
from app.schemas.health import DiagnosisCreate, DiagnosisOut
from app.services.records import require_user
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/diagnoses", tags=["diagnoses"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=DiagnosisOut, status_code=201)
def create_diagnosis(payload: DiagnosisCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    diagnosis = Diagnosis(**payload.model_dump())
    db.add(diagnosis)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="diagnosis",
            title=payload.diagnosis_name,
            description=payload.notes,
            event_date=event_datetime(payload.diagnosed_date),
        )
    )
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.get("/{user_id}")
def list_diagnoses(user_id: int, db: Session = Depends(get_db)):
    require_user(db, user_id)
    return {"items": db.query(Diagnosis).filter(Diagnosis.user_id == user_id).order_by(Diagnosis.diagnosed_date.desc()).all()}


@router.delete("/{diagnosis_id}", status_code=204)
def delete_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    db.delete(diagnosis)
    db.commit()
