from __future__ import annotations

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="en")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    medical_documents: Mapped[list["MedicalDocument"]] = relationship(back_populates="user")
    lab_results: Mapped[list["LabResult"]] = relationship(back_populates="user")
    medicines: Mapped[list["Medicine"]] = relationship(back_populates="user")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="user")
    injuries: Mapped[list["Injury"]] = relationship(back_populates="user")
    animal_bites: Mapped[list["AnimalBite"]] = relationship(back_populates="user")
    emergency_events: Mapped[list["EmergencyEvent"]] = relationship(back_populates="user")
    doctor_visits: Mapped[list["DoctorVisit"]] = relationship(back_populates="user")
    wellbeing_entries: Mapped[list["Wellbeing"]] = relationship(back_populates="user")
    timeline: Mapped[list["HealthTimeline"]] = relationship(back_populates="user")
    trusted_contacts: Mapped[list["TrustedContact"]] = relationship(back_populates="user")


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(250), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    source_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    abnormal_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="medical_documents")


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("medical_documents.id"), nullable=True)
    test_name: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="unknown")
    test_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="lab_results")
    document: Mapped[MedicalDocument | None] = relationship()


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(80), nullable=True)
    form: Mapped[str | None] = mapped_column(String(80), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dosage: Mapped[str | None] = mapped_column(String(80), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(80), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="medicines")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    diagnosis_name: Mapped[str] = mapped_column(String(180), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    diagnosed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="diagnoses")


class Injury(Base):
    __tablename__ = "injuries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    body_location: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visible_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(40), default="ASSESSMENT NEEDED")
    first_aid: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_signs: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="injuries")


class AnimalBite(Base):
    __tablename__ = "animal_bites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    animal_type: Mapped[str] = mapped_column(String(60), nullable=False)
    body_location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(40), default="ASSESSMENT NEEDED")
    first_aid: Mapped[str | None] = mapped_column(Text, nullable=True)
    rabies_awareness: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="animal_bites")


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    severity: Mapped[str] = mapped_column(String(40), default="URGENT")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="emergency_events")


class DoctorVisit(Base):
    __tablename__ = "doctor_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    visit_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="doctor_visits")


class Wellbeing(Base):
    __tablename__ = "wellbeing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    mood: Mapped[str | None] = mapped_column(String(60), nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="wellbeing_entries")


class HealthTimeline(Base):
    __tablename__ = "health_timeline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="timeline")


class TrustedContact(Base):
    __tablename__ = "trusted_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact_type: Mapped[str | None] = mapped_column("relationship", String(80), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped[User] = relationship(back_populates="trusted_contacts")


__all__ = [
    "User",
    "MedicalDocument",
    "LabResult",
    "Medicine",
    "Diagnosis",
    "Injury",
    "AnimalBite",
    "EmergencyEvent",
    "DoctorVisit",
    "Wellbeing",
    "HealthTimeline",
    "TrustedContact",
]
