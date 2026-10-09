# Architecture

The React/Vite client calls a FastAPI REST API. SQLAlchemy models persist health entities in PostgreSQL. The backend centralizes AI requests in `app.services.ai_service`, validates document uploads before storing them, and uses a dedicated OCR/extraction service. FHIR-style mapping is handled separately from route logic.

## Layers

- FastAPI routers and Pydantic request/response schemas
- SQLAlchemy models and PostgreSQL connection settings
- Centralized OmniRoute service; route modules do not call model providers directly
- Local upload storage with PDF text extraction and Tesseract image OCR
- React/Vite pages that call the backend API

Automated tests override the database URL with an isolated in-memory SQLite database. SQLite is not the application's production database configuration.

## Data flow

Document upload -> byte-size and file-content validation -> generated server-side name and local storage -> text extraction/OCR -> reviewable candidates -> user confirmation -> saved health record and timeline event.

AI-assisted explanations send only the feature's required prompt material to the configured OmniRoute endpoint. Record-grounded chat retrieves matching saved health records and returns evidence identifiers; it reports when matching evidence is absent. Emergency location sharing is an explicit, user-initiated message preparation workflow; it neither transmits nor stores a live location automatically.

## Current production blockers

The backend now authenticates accounts with Argon2 password hashes and signed, expiring HttpOnly cookies. Private ORM reads and writes are scoped to the verified account; frontend logout clears account-specific state. Independent security review, account recovery/email verification, rate limiting, audit trail, encryption-at-rest controls, and a general versioned migration system are not provided. Existing profiles require a reviewed additive schema migration and a separate verified identity-linking process before their owners can sign in.
