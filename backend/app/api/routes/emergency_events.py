from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import EmergencyEvent, HealthTimeline
from app.schemas.health import EmergencyEventCreate, EmergencyEventOut
from app.services.records import require_user
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/emergency-events", tags=["emergency-events"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=EmergencyEventOut)
def create_emergency_event(payload: EmergencyEventCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    event = EmergencyEvent(**payload.model_dump())
    db.add(event)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="emergency",
            title=payload.event_type,
            description=payload.description,
            event_date=event_datetime(None),
        )
    )
    db.commit()
    db.refresh(event)
    return event


@router.get("/{user_id}")
def list_emergency_events(user_id: int, db: Session = Depends(get_db)):
    items = db.query(EmergencyEvent).filter(EmergencyEvent.user_id == user_id).all()
    return {"items": items}
