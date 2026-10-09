# Demo flow

Use fictional accounts and synthetic health information only. Do not use real patient records in a class, portfolio, or public demonstration.

1. Start the backend and frontend using the local setup in the README.
2. Register a fictional account, then confirm the health dashboard loads for that signed-in user.
3. Add a synthetic health profile or record. Open the related records page and dashboard timeline to show the saved data flow.
4. Sign out, register or sign in as a second fictional account, and confirm that the first account's records are not shown.
5. Sign out and back in as the first account to demonstrate session restoration, then log out.
6. If demonstrating OCR, use a synthetic sample document and review extracted candidates before confirming them.
7. Demonstrate Health Q&A only with synthetic records; review the returned evidence references. Do not present generated text as a diagnosis.
8. Show Emergency SOS (Test Mode), emphasizing that it only creates local demonstration state and never contacts emergency services. Location is requested only after the user selects the location button.
9. If showing Nearby Care or Prepare Clinician Summary, demonstrate the “Update Coming Soon” notice; those frontend features are temporarily disabled.
10. Optionally show FHIR-style output and the ABDM mock, clearly identifying the latter as a mock rather than a real ABHA connection.

Do not claim that the application dispatched emergency responders, provides live tracking, verifies a clinical diagnosis, or connects to a real ABDM service.
