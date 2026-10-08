from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import HealthTimeline

router = APIRouter(prefix="/api", tags=["health-timeline"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/timeline/{user_id}")
@router.get("/health-timeline/{user_id}")
def health_timeline(user_id: int, db: Session = Depends(get_db)):
    items = db.query(HealthTimeline).filter(HealthTimeline.user_id == user_id).order_by(HealthTimeline.event_date.desc()).all()
    return {"items": items}
