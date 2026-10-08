from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import DoctorVisit, HealthTimeline, LabResult, MedicalDocument, Medicine, User
from app.schemas.health import DoctorSummaryRequest, DoctorVisitCreate, DoctorVisitOut
from app.services.ai_service import AIService, AIServiceError
from app.services.records import require_user
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/doctor-visits", tags=["doctor-visits"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=DoctorVisitOut)
def create_doctor_visit(payload: DoctorVisitCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    visit = DoctorVisit(**payload.model_dump())
    db.add(visit)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="doctor_visit",
            title=f"Doctor visit: {payload.doctor_name or 'Clinical visit'}",
            description=payload.summary or payload.reason,
            event_date=event_datetime(payload.visit_date),
        )
    )
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/{user_id}")
def list_doctor_visits(user_id: int, db: Session = Depends(get_db)):
    items = db.query(DoctorVisit).filter(DoctorVisit.user_id == user_id).all()
    return {"items": items}


@router.post("/summary")
async def create_doctor_summary(payload: DoctorSummaryRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    labs = db.query(LabResult).filter(LabResult.user_id == user.id).order_by(LabResult.test_date.desc()).limit(25).all()
    medicines = db.query(Medicine).filter(Medicine.user_id == user.id).order_by(Medicine.created_at.desc()).limit(25).all()
    documents = db.query(MedicalDocument).filter(MedicalDocument.user_id == user.id).order_by(MedicalDocument.created_at.desc()).limit(10).all()
    context = {
        "purpose": payload.purpose,
        "patient_name": user.name,
        "lab_results": [
            {
                "id": lab.id,
                "test_name": lab.test_name,
                "value": lab.value,
                "unit": lab.unit,
                "reference_range": lab.reference_range,
                "status": lab.status,
                "date": lab.test_date.isoformat() if lab.test_date else None,
            }
            for lab in labs
        ],
        "medicines": [
            {"id": med.id, "name": med.name, "strength": med.strength, "frequency": med.frequency, "start_date": med.start_date.isoformat() if med.start_date else None}
            for med in medicines
        ],
        "documents": [
            {"id": document.id, "title": document.title, "date": document.source_date.isoformat() if document.source_date else None, "summary": document.extracted_summary}
            for document in documents
        ],
    }
    try:
        summary = await AIService().generate_doctor_summary(context)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "summary": summary,
        "evidence": {
            "lab_result_ids": [lab.id for lab in labs],
            "medicine_ids": [med.id for med in medicines],
            "document_ids": [document.id for document in documents],
        },
        "review_required": True,
        "safety_note": "Review this draft for accuracy and edit it before sharing with a clinician.",
    }
