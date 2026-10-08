from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
