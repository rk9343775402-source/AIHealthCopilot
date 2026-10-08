from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.health import HealthTimeline, TrustedContact, User
from app.schemas.health import (
    LocationShareRequest,
    TrustedContactCreate,
    TrustedContactOut,
    TrustedContactUpdate,
)
from app.services.location_service import LocationSearchError, LocationService

router = APIRouter(prefix="/api", tags=["emergency-and-contacts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/trusted-contacts", response_model=dict[str, list[TrustedContactOut]])
def list_trusted_contacts(user_id: int, db: Session = Depends(get_db)):
    if not db.query(User.id).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    contacts = db.query(TrustedContact).filter(TrustedContact.user_id == user_id).order_by(TrustedContact.id).all()
    return {"items": contacts}


@router.post("/trusted-contacts", response_model=TrustedContactOut, status_code=201)
def create_trusted_contact(payload: TrustedContactCreate, db: Session = Depends(get_db)):
    if not db.query(User.id).filter(User.id == payload.user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    contact = TrustedContact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/trusted-contacts/{contact_id}", response_model=TrustedContactOut)
def update_trusted_contact(
    contact_id: int,
    payload: TrustedContactUpdate,
    db: Session = Depends(get_db),
):
    contact = db.query(TrustedContact).filter(TrustedContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Trusted contact not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/trusted-contacts/{contact_id}", status_code=204)
def delete_trusted_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(TrustedContact).filter(TrustedContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Trusted contact not found")
    db.delete(contact)
    db.commit()


@router.get("/emergency/guidance")
def emergency_guidance():
    return {
        "disclaimer": "This guidance is general and cannot assess your condition. Contact local emergency services for immediate danger.",
        "warning_signs": [
            "Trouble breathing, severe chest pain, fainting, new confusion, or stroke-like symptoms",
            "Severe bleeding that does not stop with firm direct pressure",
            "A serious head, neck, or spine injury, seizure, or sudden loss of consciousness",
            "A rapidly worsening condition or a situation that feels life-threatening",
        ],
        "remote_area_steps": [
            "Call your local emergency number and give your location and a callback number.",
            "Share GPS coordinates only if location services are available and you choose to do so.",
            "Follow instructions from emergency dispatch; do not move someone with a possible spine injury unless there is immediate danger.",
            "Ask a trusted nearby person to meet responders; do not rely on this app as an emergency service.",
        ],
        "bite_kit": [
            "Clean water and soap for prolonged wound washing",
            "Disposable gloves, sterile gauze, and a clean pressure dressing",
            "A charged phone and a written list of medicines, allergies, and emergency contacts",
        ],
        "bite_guidance": (
            "After a bite, move away from the animal without approaching it. Wash the wound thoroughly with soap and running water "
            "and seek prompt medical/public-health assessment for rabies and tetanus exposure decisions. An image cannot diagnose rabies."
        ),
    }


@router.get("/nearby-care")
async def nearby_care(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(default=10000, ge=500, le=50000),
):
    try:
        places = await LocationService().nearby_care(latitude, longitude, radius_m)
    except LocationSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "items": places,
        "source": "OpenStreetMap",
        "notice": "Map data may be incomplete or outdated. Call ahead and use local emergency services for urgent care.",
    }


@router.post("/emergency/location-share/prepare")
def prepare_location_share(payload: LocationShareRequest, db: Session = Depends(get_db)):
    contact = (
        db.query(TrustedContact)
        .filter(
            TrustedContact.id == payload.contact_id,
            TrustedContact.user_id == payload.user_id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Trusted contact not found for this user")
    map_url = f"https://www.google.com/maps?q={payload.latitude:.6f},{payload.longitude:.6f}"
    message = f"{payload.message.strip()}\n{map_url}"
    db.add(
        HealthTimeline(
            user_id=payload.user_id,
            event_type="location_share_prepared",
            title="Emergency location-share message prepared",
            description=f"A location message was prepared for trusted contact {contact.name}; it was not sent.",
        )
    )
    db.commit()
    return {
        "contact": {"id": contact.id, "name": contact.name, "phone": contact.phone},
        "message": message,
        "delivery_status": "not_sent",
        "notice": "This app does not send SMS or share location in the background. Review and send the message yourself.",
    }
