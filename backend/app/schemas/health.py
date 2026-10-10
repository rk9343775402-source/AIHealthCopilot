from __future__ import annotations

import base64
import binascii
from datetime import date, datetime
from io import BytesIO
from typing import Any, Optional

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic import BaseModel, EmailStr

def validate_image_data_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        header, encoded = value.split(",", 1)
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Image data must be a valid base64 data URL") from exc
    valid_signature = (
        header == "data:image/jpeg;base64" and content.startswith(b"\xff\xd8\xff")
        or header == "data:image/png;base64" and content.startswith(b"\x89PNG\r\n\x1a\n")
        or header == "data:image/webp;base64" and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    )
    if not valid_signature:
        raise ValueError("Image data does not match the declared image format")
    try:
        image = Image.open(BytesIO(content))
        if image.width * image.height > 25_000_000:
            raise ValueError("Image dimensions exceed the supported limit")
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Image data is not a valid, readable image") from exc
    return value


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=180)
    phone: Optional[str] = Field(default=None, max_length=40)
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    language: str = "en"

    @field_validator("email", "phone", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return None if value == "" else value


class UserOut(UserCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class AuthRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=256)
    phone: Optional[str] = Field(default=None, max_length=40)


class AuthLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)


class MedicalDocumentCreate(BaseModel):
    user_id: int
    title: str
    document_type: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    source_date: Optional[date] = None
    ocr_text: Optional[str] = None


class MedicalDocumentOut(MedicalDocumentCreate):
    id: int
    status: str
    extracted_summary: Optional[str] = None
    explanation: Optional[str] = None
    abnormal_values: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MedicalDocumentConfirmation(BaseModel):
    user_id: int
    candidate_indices: list[int] = Field(..., min_length=1, max_length=100)


class LabResultCreate(BaseModel):
    user_id: int
    test_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: str = "unknown"
    test_date: Optional[date] = None
    source_document_id: Optional[int] = None


class LabResultOut(LabResultCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class MedicineCreate(BaseModel):
    user_id: int
    name: str
    strength: Optional[str] = None
    form: Optional[str] = None
    manufacturer: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    notes: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MedicineOut(MedicineCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class InjuryCreate(BaseModel):
    user_id: int
    body_location: str
    description: Optional[str] = None
    visible_findings: Optional[str] = None


class InjuryOut(InjuryCreate):
    id: int
    urgency: str
    first_aid: Optional[str] = None
    warning_signs: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AnimalBiteCreate(BaseModel):
    user_id: int
    animal_type: str
    body_location: Optional[str] = None
    description: Optional[str] = None


class AnimalBiteOut(AnimalBiteCreate):
    id: int
    urgency: str
    first_aid: Optional[str] = None
    rabies_awareness: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EmergencyEventCreate(BaseModel):
    user_id: int
    event_type: str
    description: Optional[str] = None
    location: Optional[str] = None
    severity: str = "URGENT"


class EmergencyEventOut(EmergencyEventCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class DoctorVisitCreate(BaseModel):
    user_id: int
    doctor_name: Optional[str] = None
    reason: Optional[str] = None
    summary: Optional[str] = None
    visit_date: Optional[date] = None


class DoctorSummaryRequest(BaseModel):
    user_id: int
    purpose: Optional[str] = Field(default=None, max_length=500)


class DoctorVisitOut(DoctorVisitCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class DiagnosisCreate(BaseModel):
    user_id: int
    diagnosis_name: str = Field(..., min_length=1, max_length=180)
    notes: Optional[str] = Field(default=None, max_length=5000)
    doctor_name: Optional[str] = Field(default=None, max_length=180)
    diagnosed_date: Optional[date] = None


class DiagnosisOut(DiagnosisCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class WellbeingCreate(BaseModel):
    user_id: int
    mood: Optional[str] = None
    stress_level: Optional[int] = Field(default=None, ge=1, le=10)
    message: Optional[str] = None
    entry_date: Optional[date] = None


class WellbeingOut(WellbeingCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class HealthQuestionRequest(BaseModel):
    user_id: int
    question: str = Field(..., min_length=1)
    response_language: str = Field(default="en", pattern=r"^(en|hi)$")


class AIResponse(BaseModel):
    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    basis: str = "records"
    ai_status: Optional[str] = None


class TrustedContactCreate(BaseModel):
    user_id: int
    name: str = Field(..., min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=40)
    contact_type: Optional[str] = Field(default=None, max_length=80)


class TrustedContactUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=40)
    contact_type: Optional[str] = Field(default=None, max_length=80)


class TrustedContactOut(TrustedContactCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class LocationShareRequest(BaseModel):
    user_id: int
    contact_id: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    message: str = Field(default="I may need help. This is my current location.", max_length=500)


class ImageAnalysisRequest(BaseModel):
    image_data_url: Optional[str] = Field(default=None, min_length=32, max_length=14_000_000, pattern=r"^data:image/(jpeg|png|webp);base64,")
    description: Optional[str] = Field(default=None, max_length=2000)
    body_location: Optional[str] = Field(default=None, max_length=150)

    @field_validator("image_data_url")
    @classmethod
    def validate_image(cls, value):
        return validate_image_data_url(value)

    @model_validator(mode="after")
    def require_image_or_description(self):
        if not self.image_data_url and not (self.description and self.description.strip()):
            raise ValueError("Provide an image or a description")
        return self


class AnimalBiteAnalysisRequest(ImageAnalysisRequest):
    animal_type: Optional[str] = Field(default=None, max_length=60)


class MedicineRecognitionRequest(BaseModel):
    image_data_url: str = Field(..., min_length=32, max_length=14_000_000, pattern=r"^data:image/(jpeg|png|webp);base64,")

    @field_validator("image_data_url")
    @classmethod
    def validate_image(cls, value):
        return validate_image_data_url(value)


class AnimalRecognitionRequest(BaseModel):
    image_data_url: str = Field(..., min_length=32, max_length=14_000_000, pattern=r"^data:image/(jpeg|png|webp);base64,")
    description: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("image_data_url")
    @classmethod
    def validate_image(cls, value):
        return validate_image_data_url(value)


class WellbeingResponseRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    language: str = Field(default="en", pattern=r"^(en|hi)$")


class TranslationRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    language: str = Field(..., pattern=r"^(en|hi)$")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str