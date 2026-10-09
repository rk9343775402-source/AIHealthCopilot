# AI safety

This is a development-stage health information tool, not medical care, diagnosis, or emergency response. All model-backed features use the centralized OmniRoute service configured on the backend. A frontend/API caller cannot supply or retrieve the provider secret.

- Personal-record questions retrieve saved records and include source identifiers; when no matching records are retrieved, the service reports that limitation rather than inventing history.
- OCR output is reviewable and candidate lab results require explicit user confirmation before being saved.
- Abnormal flags rely on a reference interval present in the source. Trend outputs describe saved data and do not diagnose.
- Image features cannot establish a diagnosis, exact wound depth, or rabies status. Unclear/inaccessible AI service results are not represented as medical findings.
- Emergency workflows encourage professional assessment and do not contact emergency services. Location sharing is opt-in and prepared for the user to send.
- Crisis language in wellbeing check-ins triggers a supportive safety response without sending that message to an AI provider.
- Provider availability, model behavior, translation quality, OCR accuracy, and clinical safety require further validation before any clinical use.

When OmniRoute is enabled, relevant user-entered health text or images are sent to the configured provider. Configure consent, privacy notices, retention controls, and a provider whose terms meet the deployment's requirements before processing personal data.

The API now requires an authenticated session for private routes and scopes ORM reads and writes to the authenticated account. These application changes do not constitute an independent security/privacy review or provide account recovery, email verification, rate limiting, audit controls, or encryption-at-rest. Do not process real patient data until these remaining safeguards and applicable privacy requirements have been reviewed.
