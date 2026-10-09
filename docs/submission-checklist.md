# Project submission checklist

## Before presenting

- Follow [the README setup](../README.md) and confirm PostgreSQL credentials against the intended local server.
- Set a private, unique `AUTH_SECRET_KEY` of at least 32 random bytes. Do not include `.env` files, database passwords, provider keys, or session secrets in submission files.
- Run the backend tests and frontend production build using the commands in the README.
- Start the app and verify registration, login, logout, session restoration, dashboard loading, and record creation with fictional accounts.
- Use two fictional accounts to verify that records created by one account do not appear in the other account.
- Use synthetic documents and health values only. Do not include real or identifiable patient information in screenshots, sample data, or recordings.

## Feature boundaries to disclose

- Nearby Care and Prepare Clinician Summary are temporarily disabled in the frontend and show an “Update Coming Soon” notice. Their backend code remains in place.
- Emergency SOS is test-only, stores simulated state in the frontend, and does not contact an ambulance, emergency service, or responder.
- The ABDM screen is a mock. No real ABHA connection or data transfer is provided.
- AI output, OCR, and health-record Q&A are informational and require clinician review. AI-provider availability and external service access depend on local configuration.
- The product is a development-stage demonstration, not a medical device or production service for real patient data.

## Evidence to include

- A brief walkthrough following [the demo flow](./demo-flow.md).
- The actual test and build results from the submission environment.
- Screenshots showing only fictional account and health data.
- A concise architecture summary identifying React/Vite, FastAPI, SQLAlchemy, and PostgreSQL.

Do not report a capability as verified unless it was exercised in the submission environment. Unit tests using in-memory SQLite do not verify connectivity or authentication against a separate PostgreSQL installation.
