# Database design

The SQLAlchemy health-domain models center records on a `User` and include medical documents, lab results, medicines, diagnoses, injuries, animal bites, emergency events, doctor visits, wellbeing entries, trusted contacts, and timeline events. PostgreSQL is the application database. The application creates missing tables with SQLAlchemy `Base.metadata.create_all()` during startup.

Automated tests explicitly override `DATABASE_URL` with an isolated in-memory SQLite database. The application does not fall back to SQLite. A versioned migration system has not yet been added; `create_all()` does not modify existing tables to match model changes.

## Important security limitation

The current API has no authentication or authorization and accepts user IDs from the caller. It does not provide safe per-user access controls. Do not store real patient information or expose this database/API publicly until identity, ownership checks, least-privilege access, auditability, retention, backups, and encryption requirements are implemented and reviewed.
