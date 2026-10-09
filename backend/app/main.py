from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import SESSION_COOKIE, router as auth_router
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
from app.database.session import OwnershipViolation, SessionLocal, engine
from app.seeds.demo_data import seed_demo_data
from app.security import authenticated_user_id, get_token_user_id


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.demo_mode:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(title="AI Personal Health Copilot", version="1.0.0", docs_url="/docs", lifespan=lifespan)
allowed_origins = {
    origin.strip().rstrip("/")
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
}
allowed_origins.add("https://aihealthcopilot.onrender.com")

@app.middleware("http")
async def authenticate_api_requests(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin.rstrip("/") not in allowed_origins:
        return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed."})

    public_paths = {"/api/auth/register", "/api/auth/login"}
    user_id = None
    if request.url.path not in public_paths:
        user_id = get_token_user_id(request.cookies.get(SESSION_COOKIE, ""))
        if user_id is None:
            return JSONResponse(status_code=401, content={"detail": "Authentication required."})
        request.state.authenticated_user_id = user_id

    token = authenticated_user_id.set(user_id)
    try:
        return await call_next(request)
    finally:
        authenticated_user_id.reset(token)


@app.exception_handler(OwnershipViolation)
async def handle_ownership_violation(_request: Request, _exc: OwnershipViolation):
    return JSONResponse(status_code=404, content={"detail": "Resource not found."})


app.include_router(auth_router)
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


fastapi_app = app
app = CORSMiddleware(
    app=fastapi_app,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)
