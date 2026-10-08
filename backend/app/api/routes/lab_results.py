import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import HealthTimeline, LabResult, User
from app.schemas.health import LabResultCreate, LabResultOut
from app.services.records import require_user
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/lab-results", tags=["lab-results"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=LabResultOut)
def create_lab_result(payload: LabResultCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    lab = LabResult(**payload.model_dump())
    db.add(lab)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="lab_result",
            title=payload.test_name,
            description=f"Lab result {payload.test_name} recorded with status {payload.status}.",
            event_date=event_datetime(payload.test_date),
            metadata_json=json.dumps({"status": payload.status, "value": payload.value, "unit": payload.unit}),
        )
    )
    db.commit()
    db.refresh(lab)
    return lab


@router.get("/{user_id}")
def list_lab_results(user_id: int, db: Session = Depends(get_db)):
    items = db.query(LabResult).filter(LabResult.user_id == user_id).all()
    return {"items": items}


@router.get("/{user_id}/trends")
def lab_result_trends(user_id: int, db: Session = Depends(get_db)):
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    results = (
        db.query(LabResult)
        .filter(LabResult.user_id == user_id)
        .order_by(LabResult.test_date.asc(), LabResult.created_at.asc())
        .all()
    )
    grouped: dict[str, list[LabResult]] = defaultdict(list)
    for result in results:
        grouped[result.test_name.casefold()].append(result)
    trends = []
    for group in grouped.values():
        group.sort(key=lambda result: (result.test_date is not None, result.test_date or result.created_at.date(), result.id))
        comparable = [result for result in group if result.value is not None]
        direction = "insufficient_data"
        change = None
        if len(comparable) >= 2 and (comparable[0].unit or "").casefold() == (comparable[-1].unit or "").casefold():
            change = comparable[-1].value - comparable[0].value
            direction = "increased" if change > 0 else "decreased" if change < 0 else "unchanged"
        trends.append(
            {
                "test_name": group[0].test_name,
                "unit": group[-1].unit,
                "direction": direction,
                "change": change,
                "values": [
                    {
                        "value": result.value,
                        "unit": result.unit,
                        "status": result.status,
                        "reference_range": result.reference_range,
                        "date": result.test_date.isoformat() if result.test_date else result.created_at.isoformat(),
                        "source_document_id": result.source_document_id,
                    }
                    for result in group
                ],
                "interpretation": "Trend direction is descriptive only; clinical meaning depends on the test and your clinician's assessment.",
            }
        )
    return {"items": trends}
