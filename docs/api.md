# API overview

The backend exposes a health-focused REST interface under `/api`.

Key routes include:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `/api/users`
- `/api/medical-documents`
- `/api/lab-results`
- `/api/medicines`
- `/api/injuries`
- `/api/animal-bites`
- `/api/emergency-events`
- `/api/doctor-visits`
- `/api/wellbeing`
- `/api/health-profile/{user_id}`
- `/api/health-timeline/{user_id}`
- `/api/health-chat`
- `/api/fhir/*`
- `/api/abdm/mock/{user_id}`

The OpenAPI docs are provided by FastAPI at `/docs`.

Registration and login set a signed, expiring HttpOnly session cookie; credentials and tokens are not included in JSON responses. The React client sends credentialed requests. Private API routes require this cookie, and backend ORM reads/writes are scoped to its verified user identity. Caller-supplied IDs remain in some endpoint contracts for compatibility, but they are not accepted as proof of identity and cannot select another user's data. `POST /api/users` is no longer an account-creation route; use `/api/auth/register`.

Unsafe cross-origin requests are limited to configured `ALLOWED_ORIGINS`. Configure a strong `AUTH_SECRET_KEY` (at least 32 random bytes), `APP_ENV=production`, and the deployed frontend origin in the backend environment. Existing profiles with no password hash cannot log in until ownership is safely verified; see the migration procedure in the README.

Medical-document upload supports bounded PDF and image files. Embedded PDF text and supported image OCR are extracted for review; scanned PDF OCR is not implemented. Candidate lab results are not persisted until the user confirms them. See the OpenAPI schema for exact request bodies, limits, and response shapes.
