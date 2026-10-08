from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import HealthTimeline, Medicine, User
from app.schemas.health import MedicineCreate, MedicineOut, MedicineRecognitionRequest
from app.services.ai_service import AIService, AIServiceError
from app.services.records import require_user
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/medicines", tags=["medicines"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=MedicineOut)
def create_medicine(payload: MedicineCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    med = Medicine(**payload.model_dump())
    db.add(med)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="medicine",
            title=payload.name,
            description=f"Medicine recorded: {payload.name} {payload.strength or ''}".strip(),
            event_date=event_datetime(payload.start_date),
            metadata_json=json.dumps({"dosage": payload.dosage, "frequency": payload.frequency}),
        )
    )
    db.commit()
    db.refresh(med)
    return med


@router.get("/{user_id}")
def list_medicines(user_id: int, db: Session = Depends(get_db)):
    items = db.query(Medicine).filter(Medicine.user_id == user_id).all()
    return {"items": items}


@router.post("/recognize")
async def recognize_medicine(payload: MedicineRecognitionRequest):
    try:
        result = await AIService().recognize_medicine(payload.model_dump())
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0.8:
        result["warning"] = "Medicine could not be reliably identified. Please verify the packaging or consult a pharmacist or doctor."
    return {**result, "verified_by_user": False, "safety_note": "Do not take or add a medicine based only on image recognition; verify the label with a pharmacist or clinician."}
