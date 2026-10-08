from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import HealthTimeline, Injury
from app.schemas.health import ImageAnalysisRequest, InjuryCreate, InjuryOut
from app.services.ai_service import AIService, AIServiceError
from app.services.records import require_user

router = APIRouter(prefix="/api/injuries", tags=["injuries"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=InjuryOut)
def create_injury(payload: InjuryCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    injury = Injury(**payload.model_dump())
    injury.urgency = "NEEDS MEDICAL ASSESSMENT"
    injury.first_aid = "Clean with water and cover with a sterile dressing. Seek assessment if the wound is large or worsening."
    injury.warning_signs = "Severe pain, swelling, fever, redness spreading, or bleeding that does not stop."
    db.add(injury)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="injury",
            title=f"Injury: {payload.body_location}",
            description=payload.description,
            event_date=injury.created_at,
        )
    )
    db.commit()
    db.refresh(injury)
    return injury


@router.get("/{user_id}")
def list_injuries(user_id: int, db: Session = Depends(get_db)):
    items = db.query(Injury).filter(Injury.user_id == user_id).all()
    return {"items": items}


@router.post("/analyze")
async def analyze_injury(payload: ImageAnalysisRequest):
    try:
        result = await AIService().analyze_injury(payload.model_dump(exclude_none=True))
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "analysis": result,
        "diagnosis": None,
        "wound_depth": None,
        "safety_note": "This is not a diagnosis and cannot determine exact wound depth or internal injury. Seek urgent care for severe or worsening symptoms.",
        "review_required": True,
    }
