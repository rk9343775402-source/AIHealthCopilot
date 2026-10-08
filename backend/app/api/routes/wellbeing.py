import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import HealthTimeline, User, Wellbeing
from app.schemas.health import WellbeingCreate, WellbeingOut, WellbeingResponseRequest
from app.services.ai_service import AIService, AIServiceError
from app.services.records import require_user
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/wellbeing", tags=["wellbeing"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=WellbeingOut)
def create_wellbeing(payload: WellbeingCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    entry = Wellbeing(**payload.model_dump())
    db.add(entry)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="wellbeing",
            title=f"Wellbeing check-in: {payload.mood or 'Mood update'}",
            description=payload.message,
            event_date=event_datetime(payload.entry_date),
            metadata_json=json.dumps({"stress_level": payload.stress_level}),
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{user_id}")
def list_wellbeing(user_id: int, db: Session = Depends(get_db)):
    items = db.query(Wellbeing).filter(Wellbeing.user_id == user_id).all()
    return {"items": items}


@router.post("/response")
async def wellbeing_response(payload: WellbeingResponseRequest):
    if re.search(
        r"\b(suicid(?:e|al)|kill myself|end my life|hurt myself|self[- ]harm|can't go on)\b|"
        r"आत्महत्या|खुदकुशी|खुद को मार",
        payload.message,
        flags=re.IGNORECASE,
    ):
        response = (
            "मुझे खेद है कि आप यह सब झेल रहे हैं। मैं थेरेपिस्ट नहीं हूँ, लेकिन आपकी सुरक्षा महत्वपूर्ण है। "
            "यदि आप तत्काल खतरे में हैं या इन विचारों पर अमल कर सकते हैं, तो अभी स्थानीय आपातकालीन नंबर पर कॉल करें "
            "या नज़दीकी आपातकालीन विभाग जाएँ। यदि संभव हो, किसी भरोसेमंद व्यक्ति से संपर्क करें और उनसे साथ रहने को कहें।"
            if payload.language == "hi"
            else (
                "I’m really sorry you’re facing this. I’m not a therapist, but your safety matters. "
                "If you might act on these thoughts or are in immediate danger, call your local emergency number now "
                "or go to the nearest emergency department. If possible, contact someone you trust and ask them to stay with you."
            )
        )
        return {
            "response": response,
            "activities": [],
            "crisis_escalation": True,
            "ai_status": "safety_escalation",
            "safety_note": "This app cannot provide crisis response or monitor your safety.",
        }
    try:
        result = await AIService().wellbeing_response(payload.model_dump())
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        **result,
        "crisis_escalation": False,
        "safety_note": "This is general supportive information, not therapy or a diagnosis.",
    }
