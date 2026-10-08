# AI Personal Health Copilot

A development-stage personal health application with a FastAPI/SQLAlchemy API, PostgreSQL database, React/Vite interface, OCR workflows, and a centralized OmniRoute AI service. The application is not a medical device, a substitute for a clinician, or an emergency-response service.

## What is implemented

- Health profiles and user-scoped records for medical documents, lab results, medicines, diagnoses, visits, injuries, animal bites, emergency events, wellbeing, trusted contacts, and a unified timeline.
- PDF text extraction and English/Hindi OCR for supported images. Extracted lab candidates are shown for review and are only added to history after explicit confirmation. Image recognition and generated explanations require OmniRoute configuration.
- Lab reference-range flags and descriptive trends; these do not make a diagnosis.
- Health-record Q&A that retrieves matching saved records and returns source identifiers, plus doctor-visit summary generation.
- Injury and animal-bite intake/guidance, with explicit safety limitations; this does not diagnose from an image or diagnose rabies.
- Emergency guidance, opt-in browser geolocation, nearby-care lookup through public OpenStreetMap/Overpass services, trusted contacts, and a location message that the user must send themselves.
- FHIR-style Patient, Observation, and Bundle output, plus a clearly identified ABDM mock (no real ABHA connection or data transfer).
- A responsive, API-connected frontend. Hindi interface coverage is partial; stored records are not automatically translated.

## Important deployment and privacy limitations

**Do not use this scaffold with real patient data or expose it to the public internet.** There is no authentication, authorization, user isolation boundary, audit trail, encryption-at-rest policy, or database migration framework. The API accepts a user ID supplied by the client and its record routes do not enforce ownership. Database tables are initialized with SQLAlchemy `create_all`, which is not a schema migration strategy. These gaps must be resolved and independently reviewed before any clinical or production use.

When OmniRoute is configured, relevant user-supplied text or images are sent to the configured AI provider. Review that provider's privacy terms and configure appropriate consent and data-processing safeguards before use. Uploaded files are stored on the backend filesystem. Location lookup uses a public third-party Overpass endpoint. SMS, background location sharing, emergency dispatch, and ABHA/ABDM connectivity are not implemented.

## Run with Docker Compose (Windows PowerShell)

Requires Docker Desktop with Compose. From the project root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env and replace the POSTGRES_PASSWORD placeholder before starting.
docker compose up --build
```

Compose reads environment variables from the project-root `.env`; `POSTGRES_PASSWORD` is required. If `.env` already exists, do not overwrite it—update it while preserving local values. To enable AI features, set `OMNIROUTE_API_KEY` there; Compose passes it only to the backend. Never put AI credentials in frontend variables. `.env.example` is a safe template with placeholders, not real credentials. Never commit `.env` files or secrets.

Open the frontend at <http://localhost:5173>, the API at <http://localhost:8000>, and interactive API docs at <http://localhost:8000/docs>.

The backend container includes Tesseract English and Hindi language data. The Compose service persists PostgreSQL data and uploaded files in named volumes. The location lookup still requires access to the public Overpass API.

## Run locally

Start PostgreSQL first and create a database, then configure `backend/.env` from `backend/.env.example` with a PostgreSQL `DATABASE_URL` and any OmniRoute settings. Replace its database password placeholder with a unique URL-safe local password. `backend/.env` is for direct backend execution; Compose instead uses the project-root `.env`. `backend/.env.example` is a safe template with placeholders only. Never commit `.env` files or secrets. For image OCR, install the Tesseract executable and its `eng` language data; install `hin` as well for Hindi OCR. Scanned PDFs are not OCR'd. Handwriting recognition is not reliable and any extracted text must be checked.

In one PowerShell terminal:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Edit `backend/.env` to use the PostgreSQL database you created and replace its password placeholder. In another terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

If the API is not at `http://localhost:8000`, set `VITE_API_BASE_URL` before building/starting Vite. Vite environment variables are build/start-time configuration; the Settings field explains the configured address but does not change it.

## Tests and production build

From the repository root:

```powershell
cd backend
python -m pytest tests -q
cd ..\frontend
npm install
npm run build
```

Automated backend tests configure an isolated in-memory SQLite database only inside the test fixture. The application and Compose use PostgreSQL. The suite does not substitute for PostgreSQL integration, security, privacy, OCR-language, or clinical validation.

## External service requirements

- A reachable PostgreSQL server for application use.
- Optional OmniRoute-compatible AI service configured with `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`, and `OMNIROUTE_MODEL`.
- Tesseract with English/Hindi language data for local image OCR; the Docker image installs both languages.
- Public Overpass API access for nearby-care searches.

If OmniRoute is unconfigured, AI features return cautious unavailable responses; they do not invent medical records, lab values, medicines, diagnoses, or summaries.
