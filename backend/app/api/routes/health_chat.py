from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import (
    AnimalBite,
    Diagnosis,
    DoctorVisit,
    EmergencyEvent,
    Injury,
    LabResult,
    MedicalDocument,
    Medicine,
    User,
    Wellbeing,
)
from app.schemas.health import AIResponse, HealthQuestionRequest
from app.services.ai_service import AIService, AIServiceError

router = APIRouter(prefix="/api", tags=["health-chat"])
STOP_WORDS = {
    "a", "about", "all", "and", "are", "did", "do", "does", "for", "from", "have", "how",
    "i", "in", "is", "it", "latest", "me", "my", "of", "on", "please", "show", "tell", "the",
    "to", "was", "were", "what", "when", "where", "which", "with", "you", "your",
    "का", "की", "के", "में", "मेरी", "मेरा", "मेरे", "क्या", "है", "हैं", "था", "थी", "बताएं", "दिखाएं",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _matches(question_terms: set[str], text: str) -> bool:
    return any(term in text.casefold() for term in question_terms)


def _evidence(source_type: str, source_id: int, label: str, **fields):
    return {"source_type": source_type, "source_id": source_id, "source_label": label, **fields}


@router.post("/health-chat", response_model=AIResponse)
async def health_chat(payload: HealthQuestionRequest, db: Session = Depends(get_db)):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    terms = {
        term for term in re.findall(r"[a-z0-9\u0900-\u097f]+", question.casefold())
        if len(term) > 1 and term not in STOP_WORDS
    }
    question_lower = question.casefold()
    lab_query = bool(re.search(r"\b(lab|labs|test|tests|result|results|blood|hemoglobin|cholesterol|ldl|hdl|glucose|a1c)\b|रिपोर्ट|जांच|जाँच|प्रयोगशाला|खून|रक्त", question_lower))
    medicine_query = bool(re.search(r"\b(medicine|medicines|medication|medications|drug|drugs|tablet|dose)\b|दवा|दवाइ|औषधि|गोली", question_lower))
    injury_query = bool(re.search(r"\b(injury|injuries|wound|bite|bites)\b|चोट|घाव|काटने|काटना", question_lower))

    context: list[dict] = []
    labs = db.query(LabResult).filter(LabResult.user_id == user.id).order_by(LabResult.test_date.desc()).limit(100).all()
    for record in labs:
        searchable = f"{record.test_name} {record.status} {record.unit or ''}"
        if lab_query or _matches(terms, searchable):
            context.append(
                _evidence(
                    "lab_result",
                    record.id,
                    record.test_name,
                    value=record.value,
                    unit=record.unit,
                    reference_range=record.reference_range,
                    status=record.status,
                    date=record.test_date.isoformat() if record.test_date else None,
                    document_id=record.source_document_id,
                )
            )

    medicines = db.query(Medicine).filter(Medicine.user_id == user.id).order_by(Medicine.created_at.desc()).limit(100).all()
    for med in medicines:
        searchable = f"{med.name} {med.strength or ''} {med.form or ''} {med.frequency or ''}"
        if medicine_query or _matches(terms, searchable):
            context.append(
                _evidence(
                    "medicine",
                    med.id,
                    med.name,
                    strength=med.strength,
                    dosage=med.dosage,
                    frequency=med.frequency,
                    duration=med.duration,
                    start_date=med.start_date.isoformat() if med.start_date else None,
                    end_date=med.end_date.isoformat() if med.end_date else None,
                )
            )

    documents = db.query(MedicalDocument).filter(MedicalDocument.user_id == user.id).order_by(MedicalDocument.created_at.desc()).limit(100).all()
    for document in documents:
        searchable = f"{document.title} {document.document_type} {document.extracted_summary or ''} {document.explanation or ''}"
        if _matches(terms, searchable):
            context.append(
                _evidence(
                    "medical_document",
                    document.id,
                    document.title,
                    document_type=document.document_type,
                    source_date=document.source_date.isoformat() if document.source_date else None,
                    summary=document.extracted_summary,
                    explanation=document.explanation,
                )
            )

    if injury_query or _matches(terms, "injury bite wound"):
        for record in db.query(Injury).filter(Injury.user_id == user.id).order_by(Injury.created_at.desc()).limit(50).all():
            context.append(_evidence("injury", record.id, f"Injury: {record.body_location}", description=record.description, urgency=record.urgency, date=record.created_at.isoformat()))
        for record in db.query(AnimalBite).filter(AnimalBite.user_id == user.id).order_by(AnimalBite.created_at.desc()).limit(50).all():
            context.append(_evidence("animal_bite", record.id, f"Animal bite: {record.animal_type}", body_location=record.body_location, description=record.description, urgency=record.urgency, date=record.created_at.isoformat()))

    for record in db.query(Diagnosis).filter(Diagnosis.user_id == user.id).order_by(Diagnosis.diagnosed_date.desc()).limit(50).all():
        if _matches(terms, f"{record.diagnosis_name} {record.notes or ''}"):
            context.append(_evidence("diagnosis", record.id, record.diagnosis_name, notes=record.notes, doctor=record.doctor_name, date=record.diagnosed_date.isoformat() if record.diagnosed_date else None))
    for record in db.query(DoctorVisit).filter(DoctorVisit.user_id == user.id).order_by(DoctorVisit.visit_date.desc()).limit(50).all():
        if _matches(terms, f"{record.reason or ''} {record.summary or ''} {record.doctor_name or ''}"):
            context.append(_evidence("doctor_visit", record.id, record.reason or "Doctor visit", summary=record.summary, doctor=record.doctor_name, date=record.visit_date.isoformat() if record.visit_date else None))
    for record in db.query(EmergencyEvent).filter(EmergencyEvent.user_id == user.id).order_by(EmergencyEvent.created_at.desc()).limit(50).all():
        if _matches(terms, f"{record.event_type} {record.description or ''}"):
            context.append(_evidence("emergency_event", record.id, record.event_type, description=record.description, date=record.created_at.isoformat()))
    for record in db.query(Wellbeing).filter(Wellbeing.user_id == user.id).order_by(Wellbeing.entry_date.desc()).limit(50).all():
        if _matches(terms, f"{record.mood or ''} {record.message or ''}"):
            context.append(_evidence("wellbeing", record.id, record.mood or "Wellbeing check-in", message=record.message, stress_level=record.stress_level, date=record.entry_date.isoformat() if record.entry_date else None))

    if not context:
        return AIResponse(
            answer=(
                "आपके स्वास्थ्य रिकॉर्ड में इस प्रश्न से संबंधित जानकारी नहीं मिली। कोई चिकित्सकीय जानकारी अनुमान से नहीं जोड़ी गई।"
                if payload.response_language == "hi"
                else "I couldn't find information relevant to that question in your health records. No medical information was inferred."
            ),
            basis="records",
            evidence=[],
            ai_status="no_evidence",
        )
    try:
        result = await AIService().answer_health_question(question, context, payload.response_language)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        **result,
        "evidence": context[:50],
        "basis": "records",
        "ai_status": result.get("ai_status", "configured"),
    }
