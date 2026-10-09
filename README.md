# AI Personal Health Copilot

A development-stage personal health application with a FastAPI/SQLAlchemy API, PostgreSQL database, React/Vite interface, OCR workflows, and a centralized OmniRoute AI service. The application is not a medical device, a substitute for a clinician, or an emergency-response service.

## What is implemented

- Health profiles and user-scoped records for medical documents, lab results, medicines, diagnoses, visits, injuries, animal bites, emergency events, wellbeing, trusted contacts, and a unified timeline.
- PDF text extraction and English/Hindi OCR for supported images. Extracted lab candidates are shown for review and are only added to history after explicit confirmation. Image recognition and generated explanations require OmniRoute configuration.
- Lab reference-range flags and descriptive trends; these do not make a diagnosis.
- Health-record Q&A that retrieves matching saved records and returns source identifiers. Prepare Clinician Summary is temporarily disabled in the frontend and displays an update notice.
- Injury and animal-bite intake/guidance, with explicit safety limitations; this does not diagnose from an image or diagnose rabies.
- Emergency guidance, opt-in browser geolocation, trusted contacts, and a location message that the user must send themselves. Nearby Care is temporarily disabled in the frontend and displays an update notice. Emergency SOS is a local-only test screen and does not contact emergency services.
- FHIR-style Patient, Observation, and Bundle output, plus a clearly identified ABDM mock (no real ABHA connection or data transfer).
- A responsive, API-connected frontend. Hindi interface coverage is partial; stored records are not automatically translated.

## Important deployment and privacy limitations

Authentication now uses an Argon2 password hash and a signed, expiring, HttpOnly session cookie. Backend ORM requests are scoped to the authenticated user and writes reject mismatched owner IDs. This is not a complete production security program: independent security review, email verification/account recovery, rate limiting, audit controls, encryption-at-rest policy, retention, backups, and PostgreSQL integration testing are still required before using real patient data or making clinical claims. `create_all` creates missing tables but does not modify existing schemas.

### Authentication deployment and database upgrade

Authentication requires a unique `AUTH_SECRET_KEY` of at least 32 random bytes, `AUTH_TOKEN_EXPIRE_MINUTES` (1–1440; default 720), `APP_ENV=production` for Secure cookies, and an exact frontend origin in `ALLOWED_ORIGINS`. Configure these in the backend's Render environment; never place the session secret in frontend variables or commit it.

Existing installations require a reviewed, additive PostgreSQL migration before deploying the new backend:

1. Take and verify a database backup. Check for case-insensitive duplicate non-null emails with `SELECT lower(email), count(*) FROM users WHERE email IS NOT NULL GROUP BY lower(email) HAVING count(*) > 1;`. Resolve any duplicate identities through a verified process before continuing.
2. During a maintenance window, have a database administrator review and apply `backend/migrations/001_add_user_password_hash.sql`. It adds a nullable password-hash column and a case-insensitive email uniqueness index; it does not delete or rewrite health data. The index creation can fail if duplicates remain. Do not expect startup `create_all` to perform this migration.
3. Configure the Render secret and production cookie/CORS settings, then deploy the backend and frontend together. Do not deploy the auth-enforcing backend before the migration and secret are ready: private API requests otherwise fail closed.
4. Existing profiles receive no password during migration and cannot log in. Do not assign passwords or let users claim legacy records solely by knowing an email address. Keep those profiles inaccessible until a separately verified account-recovery/identity-linking process is designed and reviewed. No recovery flow is included in this change.

No production database migration, deployment, or account conversion was run as part of this work.

When OmniRoute is configured, relevant user-supplied text or images are sent to the configured AI provider. Review that provider's privacy terms and configure appropriate consent and data-processing safeguards before use. Uploaded files are stored on the backend filesystem. Location lookup uses a public third-party Overpass endpoint. SMS, background location sharing, emergency dispatch, and ABHA/ABDM connectivity are not implemented.

## Run with Docker Compose (Windows PowerShell)

Requires Docker Desktop with Compose. From the project root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env; set unique POSTGRES_PASSWORD and AUTH_SECRET_KEY values before starting.
docker compose up --build
```

Compose reads environment variables from the project-root `.env`; `POSTGRES_PASSWORD` and `AUTH_SECRET_KEY` are required. Generate a unique random `AUTH_SECRET_KEY` with at least 32 bytes (for example, `openssl rand -hex 32`) and keep it private. If `.env` already exists, do not overwrite it—update it while preserving local values. To enable AI features, set `OMNIROUTE_API_KEY` there; Compose passes it only to the backend. Never put AI credentials in frontend variables. `.env.example` is a safe template with placeholders, not real credentials. Never commit `.env` files or secrets.

PostgreSQL initializes its database role password only when the data volume is first created. If the volume already exists, changing `POSTGRES_PASSWORD` in `.env` does **not** change the password stored by PostgreSQL; use the existing role password or perform a separately planned local password reset. For direct local backend runs, the connection password belongs in `backend/.env`'s `DATABASE_URL`, and must match the password of the PostgreSQL role on that server. If the password contains reserved URL characters, percent-encode it in the URL. Never paste credentials into issue reports, chat, or terminal output.

Open the frontend at <http://localhost:5173>, the API at <http://localhost:8000>, and interactive API docs at <http://localhost:8000/docs>.

The backend container includes Tesseract English and Hindi language data. The Compose service persists PostgreSQL data and uploaded files in named volumes. The location lookup still requires access to the public Overpass API.

## Run locally

Start PostgreSQL first and create the `ai_health_copilot` database, then configure `backend/.env` from `backend/.env.example`. Set `DATABASE_URL` to the connection string for the local server and use the actual PostgreSQL role password for that instance; do not invent a new URL password unless you also update the PostgreSQL role through a planned local-only operation. Set a unique `AUTH_SECRET_KEY` of at least 32 random bytes. The old `SECRET_KEY` name does not configure session authentication. Use `APP_ENV=development` for local HTTP development and `APP_ENV=production` behind HTTPS. `backend/.env` is for direct backend execution; Compose instead uses the project-root `.env`, which requires `POSTGRES_PASSWORD` and `AUTH_SECRET_KEY`. The checked-in environment examples contain placeholders only. Never commit `.env` files or secrets. For image OCR, install the Tesseract executable and its `eng` language data; install `hin` as well for Hindi OCR. Scanned PDFs are not OCR'd. Handwriting recognition is not reliable and any extracted text must be checked.

The local PostgreSQL check for this workspace found that PostgreSQL 18 is running, loopback connections require SCRAM password authentication, and PostgreSQL rejects the password currently saved in ignored `backend/.env` for role `postgres`. The database files and data do not need to be replaced. If you know the current role password, connect with `psql -h 127.0.0.1 -U postgres -d postgres`, run `\password postgres` (psql hides both new-password prompts), and then update only `DATABASE_URL` in `backend/.env` to the new password, URL-encoding reserved characters. Verify with `psql -h 127.0.0.1 -U postgres -d ai_health_copilot -W -c "SELECT 1"`; the `-W` prompt does not put the password in command history. Never paste the password into chat or a command argument.

If you do not know the existing local role password, have a local administrator perform a short, local-only recovery. Stop the app, back up `C:\Program Files\PostgreSQL\18\data\pg_hba.conf`, and temporarily add this rule *above* the existing loopback host rule: `host ai_health_copilot postgres 127.0.0.1/32 trust`. Restart service `postgresql-x64-18`, connect using `psql -h 127.0.0.1 -U postgres -d ai_health_copilot`, run `\password postgres`, and quit. Immediately restore the exact `pg_hba.conf` backup and restart the service again. Then update only `DATABASE_URL` in `backend/.env` and verify with the password-prompting `psql` command above. Keep the trust window to a minimum and do not use this procedure on a shared/untrusted machine; it temporarily allows local processes to act as that role for that one database. This changes credentials only, not database contents. Do not change the data directory, delete the database, or use this recovery procedure on production. For a pre-existing Compose volume, changing the project `.env` likewise cannot reset the password stored by PostgreSQL.

If the local PostgreSQL database predates password authentication, start the backend once so `create_all()` can create any missing tables, then apply the additive authentication migration locally after taking a backup and checking for case-insensitive duplicate email addresses:

```powershell
psql -h localhost -p 5432 -U postgres -d ai_health_copilot -W -f backend/migrations/001_add_user_password_hash.sql
```

`psql` prompts for the database password without putting it in the command or shell history. This step is only for your local database; do not run this command against production without the separately documented DBA review and backup procedure. If the lowercased-email unique index fails due to duplicate legacy addresses, stop and resolve account ownership safely rather than merging or deleting profiles.

In one PowerShell terminal:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Edit `backend/.env` to use the PostgreSQL database you created and its current role password. Start the backend from the `backend` directory so the configured `.env` is loaded. In another terminal:

```powershell
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

The frontend toolchain requires Node.js 20.19.x, 22.12 or newer in the 22.x line, or 24 or newer.
If the API is not at `http://localhost:8000`, set `VITE_API_BASE_URL` before building/starting Vite. Vite environment variables are build/start-time configuration; the Settings page shows the configured address as read-only.

## Tests and production build

Frontend component tests use Vitest, React Testing Library, and jsdom. They mock HTTP responses and cover registration, authenticated dashboard requests, logout/login, and expired-session handling; they do not replace browser-to-running-backend verification. The normal backend suite uses in-memory SQLite. PostgreSQL integration tests use only a dedicated database named exactly `ai_health_copilot_test`, never the configured app database, and add synthetic test rows without dropping or truncating tables.

Create a separate, empty local test database (the password is requested interactively):

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\createdb.exe' -W -h 127.0.0.1 -p 5432 -U postgres ai_health_copilot_test
Copy-Item backend/.env.test.example backend/.env.test
# Edit backend/.env.test locally; set TEST_DATABASE_URL to this test database only.
```

From the repository root, run the checks:

```powershell
cd backend
python -m pytest tests -q
python -m pytest -m postgres_integration tests/test_postgres_integration.py -q
cd ..\frontend
npm ci
npm test
npm run build
```

The PostgreSQL integration test is skipped if `TEST_DATABASE_URL` and `backend/.env.test` are both absent. It refuses to run unless the configured database name is exactly `ai_health_copilot_test`; never point it at production, staging, or the application database. `Base.metadata.create_all()` creates missing test tables only; the test does not run migrations or delete existing rows. If the test database already has an old/incompatible schema, create a fresh dedicated test database rather than applying changes to another environment.

For a focused presentation walkthrough and pre-submission checks, see [docs/submission-checklist.md](./docs/submission-checklist.md). The documented test/build commands validate the code in this repository; they do not prove that a local PostgreSQL installation, external AI provider, or public location service is reachable.

## External service requirements

- A reachable PostgreSQL server for application use.
- Optional OmniRoute-compatible AI service configured with `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`, and `OMNIROUTE_MODEL`.
- Tesseract with English/Hindi language data for local image OCR; the Docker image installs both languages.
- Public Overpass API access only if the temporarily disabled Nearby Care feature is re-enabled.

### Temporary Overpass connectivity diagnostic

The OpenStreetMap wiki's [Public Overpass API instances list](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances)
documents the VK Maps public API endpoint:
`https://maps.mail.ru/osm/tools/overpass/api/interpreter`.
To compare outbound HTTPS connectivity from the backend's own Render environment,
deploy the diagnostic module and run this once in that backend service's Render
Shell:

```sh
python -m app.diagnostics.overpass_connectivity
```

It checks DNS and sends the same tiny fixed `[out:json];out count;` query to
the configured production endpoint and the documented mirror. It does not use
user coordinates or health data, read response bodies, or change the production
lookup. Its output is limited to the host, DNS category, connection outcome,
HTTP status, and sanitized exception class/errno. This is a manual diagnostic,
not an API route; run it only when needed. A result from a local machine does not
establish connectivity from Render.

If OmniRoute is unconfigured, AI features return cautious unavailable responses; they do not invent medical records, lab values, medicines, diagnoses, or summaries.
