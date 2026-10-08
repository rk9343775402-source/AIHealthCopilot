from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.abdm import router as abdm_router
from app.api.routes.animal_bites import router as animal_bites_router
from app.api.routes.doctor_visits import router as doctor_visits_router
from app.api.routes.diagnoses import router as diagnoses_router
from app.api.routes.emergency import router as emergency_router
from app.api.routes.emergency_events import router as emergency_events_router
from app.api.routes.fhir import router as fhir_router
from app.api.routes.health_chat import router as health_chat_router
from app.api.routes.health_profile import router as health_profile_router
from app.api.routes.injuries import router as injuries_router
from app.api.routes.lab_results import router as lab_results_router
from app.api.routes.medical_documents import router as medical_documents_router
from app.api.routes.medicines import router as medicines_router
from app.api.routes.timeline import router as timeline_router
from app.api.routes.translation import router as translation_router
from app.api.routes.users import router as users_router
from app.api.routes.wellbeing import router as wellbeing_router
from app.core.config import settings
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.seeds.demo_data import seed_demo_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.demo_mode:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(title="AI Personal Health Copilot", version="1.0.0", docs_url="/docs", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(medical_documents_router)
app.include_router(lab_results_router)
app.include_router(medicines_router)
app.include_router(injuries_router)
app.include_router(animal_bites_router)
app.include_router(emergency_events_router)
app.include_router(emergency_router)
app.include_router(doctor_visits_router)
app.include_router(diagnoses_router)
app.include_router(wellbeing_router)
app.include_router(health_profile_router)
app.include_router(timeline_router)
app.include_router(translation_router)
app.include_router(health_chat_router)
app.include_router(fhir_router)
app.include_router(abdm_router)


@app.get("/")
def root():
    return {"app": "AI Personal Health Copilot", "status": "online", "demo_mode": settings.demo_mode}
