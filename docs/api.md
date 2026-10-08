# API overview

The backend exposes a health-focused REST interface under `/api`.

Key routes include:

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

The routes provide create/list or feature workflows rather than a complete authenticated CRUD contract for every resource. Many endpoints use caller-supplied user IDs. Until authentication, authorization, and ownership checks are implemented, do not expose the API to untrusted clients or use it for real patient data.

Medical-document upload supports bounded PDF and image files. Embedded PDF text and supported image OCR are extracted for review; scanned PDF OCR is not implemented. Candidate lab results are not persisted until the user confirms them. See the OpenAPI schema for exact request bodies, limits, and response shapes.
