# Database design

The SQLAlchemy health-domain models center records on a `User` and include medical documents, lab results, medicines, diagnoses, injuries, animal bites, emergency events, doctor visits, wellbeing entries, trusted contacts, and timeline events. PostgreSQL is the application database. The application creates missing tables with SQLAlchemy `Base.metadata.create_all()` during startup. User password hashes are stored in a nullable `password_hash` column; plaintext passwords and session tokens are not stored in database rows.

Automated tests explicitly override `DATABASE_URL` with an isolated in-memory SQLite database. The application does not fall back to SQLite. There is no general versioned migration framework; `create_all()` does not modify existing tables to match model changes. The additive PostgreSQL SQL migration at `backend/migrations/001_add_user_password_hash.sql` must be reviewed/applied before deploying auth code to an existing database. It adds a nullable column and lowercased-email uniqueness index and can fail if case-insensitive duplicate emails exist.

## Authentication and migration safety

The API requires a signed, expiring HttpOnly session cookie for private routes. ORM query criteria and write guards scope user rows and user-owned health records to the verified session identity; request-supplied user IDs cannot grant ownership. These application-level controls do not replace independent review, database least-privilege, auditability, retention, backups, or encryption-at-rest controls.

The schema migration intentionally leaves existing `password_hash` values null. Existing profile owners must not be assigned or allowed to claim accounts based only on an email string; an independently verified recovery/linking process is required. Back up PostgreSQL and check for duplicate case-insensitive email addresses before applying the migration. Do not run it automatically against production without DBA review and a maintenance plan.
