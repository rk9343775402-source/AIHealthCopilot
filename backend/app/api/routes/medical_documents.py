from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.health import HealthTimeline, LabResult, MedicalDocument, User
from app.schemas.health import MedicalDocumentConfirmation, MedicalDocumentCreate, MedicalDocumentOut
from app.services.ai_service import AIService, AIServiceError
from app.services.ocr_service import OCRService, OCRUnavailableError
from app.services.timeline_service import event_datetime

router = APIRouter(prefix="/api/medical-documents", tags=["medical-documents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=MedicalDocumentOut)
def create_document(payload: MedicalDocumentCreate, db: Session = Depends(get_db)):
    if not db.query(User.id).filter(User.id == payload.user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    doc = MedicalDocument(**payload.model_dump())
    db.add(doc)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="medical_document",
            title=payload.title,
            description=f"Added medical document: {payload.document_type}",
            event_date=event_datetime(payload.source_date),
            metadata_json=json.dumps({"document_id": doc.id, "status": doc.status}),
        )
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/upload", response_model=MedicalDocumentOut, status_code=201)
async def upload_document(
    user_id: int = Form(...),
    title: str = Form(..., min_length=1, max_length=180),
    document_type: str = Form(..., min_length=1, max_length=80),
    source_date: date | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")

    content = await file.read(settings.max_upload_size + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(content) > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="The uploaded file exceeds the configured size limit")

    signatures = (
        (b"%PDF-", "application/pdf"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"\xff\xd8\xff", "image/jpeg"),
    )
    detected_mime = next((mime for signature, mime in signatures if content.startswith(signature)), None)
    if detected_mime is None and len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        detected_mime = "image/webp"
    if detected_mime is None:
        raise HTTPException(status_code=415, detail="Unsupported file format. Upload a PDF, JPEG, PNG, or WebP.")
    if file.content_type not in {None, "", "application/octet-stream", detected_mime}:
        raise HTTPException(status_code=415, detail="The file content does not match its declared media type")

    try:
        ocr_text, ocr_engine = OCRService.extract_text(content, detected_mime)
    except OCRUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="The uploaded document could not be parsed") from exc

    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    generated_name = f"{uuid4().hex}{Path(file.filename or '').suffix.lower()[:10]}"
    destination = upload_dir / generated_name
    destination.write_bytes(content)
    original_name = Path(file.filename or "medical-document").name[:180]
    document = MedicalDocument(
        user_id=user_id,
        title=title.strip(),
        document_type=document_type.strip(),
        file_name=original_name,
        storage_path=generated_name,
        mime_type=detected_mime,
        source_date=source_date,
        ocr_text=ocr_text,
        status="text_extracted",
        extracted_summary=f"Text extracted using {ocr_engine}. Please verify it against the original document.",
    )
    db.add(document)
    db.flush()
    db.add(
        HealthTimeline(
            user_id=user_id,
            event_type="medical_document",
            title=document.title,
            description=f"Uploaded medical document: {document.document_type}",
            event_date=event_datetime(source_date),
            metadata_json=json.dumps({"document_id": document.id, "status": document.status}),
        )
    )
    try:
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return document


@router.get("/{user_id}", response_model=dict[str, list[MedicalDocumentOut]])
def list_documents(user_id: int, db: Session = Depends(get_db)):
    docs = db.query(MedicalDocument).filter(MedicalDocument.user_id == user_id).all()
    return {"items": docs}


@router.post("/{document_id}/analyze")
async def analyze_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status == "confirmed":
        raise HTTPException(status_code=409, detail="This document's extracted results have already been confirmed")
    text = document.ocr_text or ""
    if not text and document.storage_path:
        stored_file = Path(settings.upload_dir).resolve() / document.storage_path
        if not stored_file.is_file():
            raise HTTPException(status_code=404, detail="Stored document file is missing")
        try:
            text, _ = OCRService.extract_text(stored_file.read_bytes(), document.mime_type or "")
        except OCRUnavailableError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    processed = OCRService.process_document(text)
    ai_service = AIService()
    try:
        explanation = await ai_service.summarize_document(text)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    candidates = processed["detected_tests"]
    abnormal_values = [
        {"name": candidate["name"], "status": candidate["status"], "source_text": candidate["source_text"]}
        for candidate in candidates
        if candidate["status"] in {"high", "low"}
    ]

    document.status = "needs_review"
    document.extracted_summary = processed["summary"]
    document.explanation = explanation.get("summary", processed["summary"])
    document.abnormal_values = json.dumps(abnormal_values, ensure_ascii=False)
    document.ocr_text = processed["clean_text"] or document.ocr_text
    db.add(document)

    db.add(document)
    db.commit()
    return {
        "document_id": document.id,
        "processing": processed,
        "explanation": explanation,
        "abnormal_values": abnormal_values,
        "review_required": True,
        "confirmation_endpoint": f"/api/medical-documents/{document.id}/confirm",
    }


@router.post("/{document_id}/confirm")
def confirm_document_results(
    document_id: int,
    payload: MedicalDocumentConfirmation,
    db: Session = Depends(get_db),
):
    document = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.id == document_id, MedicalDocument.user_id == payload.user_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found for this user")
    if document.status == "confirmed":
        raise HTTPException(status_code=409, detail="This document's results have already been confirmed")
    if document.status != "needs_review":
        raise HTTPException(status_code=409, detail="Analyze the document and review its candidates before confirming results")
    candidates = OCRService.extract_lab_candidates(document.ocr_text or "")
    if any(index < 0 or index >= len(candidates) for index in payload.candidate_indices):
        raise HTTPException(status_code=422, detail="A selected extraction candidate does not exist")
    selected = [candidates[index] for index in dict.fromkeys(payload.candidate_indices)]
    document_id = document.id
    document_user_id = document.user_id
    document_title = document.title
    document_type = document.document_type
    source_date = document.source_date
    db.commit()
    claim = db.execute(
        update(MedicalDocument)
        .where(
            MedicalDocument.id == document_id,
            MedicalDocument.user_id == document_user_id,
            MedicalDocument.status == "needs_review",
        )
        .values(status="confirmed")
        .execution_options(synchronize_session=False)
    )
    if claim.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="This document's results have already been confirmed")

    try:
        for item in selected:
            lab = LabResult(
                user_id=document_user_id,
                source_document_id=document_id,
                test_name=item["name"],
                value=item.get("value"),
                unit=item.get("unit"),
                reference_range=item.get("reference_range"),
                status=item.get("status", "unknown"),
                test_date=source_date or date.today(),
            )
            db.add(lab)
        db.add(
            HealthTimeline(
                user_id=document_user_id,
                event_type="medical_document_confirmed",
                title=document_title,
                description=f"User confirmed {len(selected)} extracted laboratory result(s) from {document_type}.",
                event_date=event_datetime(source_date),
                metadata_json=json.dumps({"document_id": document_id, "status": "confirmed", "result_count": len(selected)}),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "document_id": document_id,
        "status": "confirmed",
        "confirmed_results": selected,
    }
