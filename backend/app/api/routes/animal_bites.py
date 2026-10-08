from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import AnimalBite, HealthTimeline
from app.schemas.health import AnimalBiteAnalysisRequest, AnimalBiteCreate, AnimalBiteOut, AnimalRecognitionRequest
from app.services.ai_service import AIService, AIServiceError
from app.services.records import require_user

router = APIRouter(prefix="/api/animal-bites", tags=["animal-bites"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=AnimalBiteOut)
def create_animal_bite(payload: AnimalBiteCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    bite = AnimalBite(**payload.model_dump())
    bite.urgency = "ASSESSMENT NEEDED"
    bite.first_aid = "Move away from the animal. Wash the wound thoroughly with soap and running water, control bleeding with clean direct pressure, and seek prompt medical assessment."
    bite.rabies_awareness = "Rabies exposure cannot be determined from an image. Contact a clinician or public-health service promptly to assess rabies and tetanus prevention."
    db.add(bite)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="animal_bite",
            title=f"Animal bite: {payload.animal_type}",
            description=payload.description,
            event_date=bite.created_at,
        )
    )
    db.commit()
    db.refresh(bite)
    return bite


@router.get("/{user_id}")
def list_animal_bites(user_id: int, db: Session = Depends(get_db)):
    items = db.query(AnimalBite).filter(AnimalBite.user_id == user_id).all()
    return {"items": items}


@router.post("/analyze")
async def analyze_animal_bite(payload: AnimalBiteAnalysisRequest):
    try:
        result = await AIService().analyze_animal_bite(payload.model_dump(exclude_none=True))
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "analysis": result,
        "rabies_diagnosis": None,
        "safety_note": "A photo cannot diagnose rabies or reliably determine exposure risk. Do not approach an animal for a photo. Seek prompt professional exposure assessment after a bite.",
        "review_required": True,
    }


@router.post("/recognize-animal")
async def recognize_animal(payload: AnimalRecognitionRequest):
    try:
        result = await AIService().recognize_animal(payload.model_dump(exclude_none=True))
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "recognition": result,
        "safety_note": "Identification may be wrong. Do not approach or handle an animal based on this result.",
    }
