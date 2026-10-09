from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.security import authenticated_user_id
from app.models.health import (
    AnimalBite,
    Diagnosis,
    DoctorVisit,
    EmergencyEvent,
    HealthTimeline,
    Injury,
    LabResult,
    MedicalDocument,
    Medicine,
    TrustedContact,
    User,
    Wellbeing,
)


class OwnershipViolation(Exception):
    pass


class TenantSession(Session):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        tenant_id = authenticated_user_id.get()
        if tenant_id is not None:
            self.info["authenticated_user_id"] = tenant_id


def _normalize_database_url(database_url: str) -> URL:
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


engine_options = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
        engine_options["poolclass"] = StaticPool
engine = create_engine(_normalize_database_url(settings.database_url), **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=TenantSession)


_TENANT_MODELS = (
    MedicalDocument,
    LabResult,
    Medicine,
    Diagnosis,
    Injury,
    AnimalBite,
    EmergencyEvent,
    DoctorVisit,
    Wellbeing,
    HealthTimeline,
    TrustedContact,
)


@event.listens_for(TenantSession, "do_orm_execute")
def _scope_tenant_queries(execute_state):
    tenant_id = execute_state.session.info.get("authenticated_user_id")
    if tenant_id is None or not (execute_state.is_select or execute_state.is_update or execute_state.is_delete):
        return
    statement = execute_state.statement.options(
        with_loader_criteria(User, lambda model: model.id == tenant_id, include_aliases=True)
    )
    for model in _TENANT_MODELS:
        statement = statement.options(
            with_loader_criteria(model, lambda entity: entity.user_id == tenant_id, include_aliases=True)
        )
    execute_state.statement = statement


@event.listens_for(TenantSession, "before_flush")
def _enforce_tenant_writes(session, _flush_context, _instances):
    tenant_id = session.info.get("authenticated_user_id")
    if tenant_id is None:
        return
    for instance in session.new.union(session.dirty).union(session.deleted):
        if isinstance(instance, User):
            if instance.id != tenant_id or instance in session.new:
                raise OwnershipViolation()
            continue
        if hasattr(instance, "user_id") and instance.user_id != tenant_id:
            raise OwnershipViolation()
        if isinstance(instance, LabResult) and instance.source_document_id is not None:
            owner_id = session.connection().execute(
                select(MedicalDocument.user_id).where(MedicalDocument.id == instance.source_document_id)
            ).scalar_one_or_none()
            if owner_id != tenant_id:
                raise OwnershipViolation()
