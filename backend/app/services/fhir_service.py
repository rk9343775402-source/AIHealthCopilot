from __future__ import annotations

from datetime import datetime
from typing import Any


class FHIRService:
    @staticmethod
    def patient_to_fhir(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "resourceType": "Patient",
            "id": str(user["id"]),
            "active": True,
            "name": [{"text": user["name"]}],
            **({"gender": user["gender"].lower()} if user.get("gender") and user["gender"].lower() in {"male", "female", "other", "unknown"} else {}),
            "telecom": ([{"system": "phone", "value": user["phone"]}] if user.get("phone") else []),
            "address": ([{"text": user["location"]}] if user.get("location") else []),
            "communication": [{"language": {"text": user.get("language") or "en"}}],
        }

    @staticmethod
    def observations_to_fhir(results: list[dict[str, Any]]) -> dict[str, Any]:
        entries = []
        for result in results:
            resource = {
                "resourceType": "Observation",
                "id": str(result.get("id")),
                "status": "final",
                "code": {"text": result.get("test_name")},
                "subject": {"reference": f"Patient/{result.get('user_id')}"} if result.get("user_id") else None,
                "referenceRange": [{"text": result["reference_range"]}] if result.get("reference_range") else [],
            }
            if result.get("value") is not None:
                resource["valueQuantity"] = {
                    "value": result["value"],
                    "unit": result.get("unit") or "",
                    "system": "http://unitsofmeasure.org",
                }
            if result.get("test_date"):
                resource["effectiveDateTime"] = result["test_date"].isoformat() if isinstance(result["test_date"], datetime) else str(result["test_date"])
            entries.append(
                {
                    "resource": resource
                }
            )
        return {"resourceType": "Bundle", "type": "collection", "entry": entries}

    @staticmethod
    def patient_bundle(user: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
        patient = FHIRService.patient_to_fhir(user)
        observations = FHIRService.observations_to_fhir(results)["entry"]
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": patient}, *observations],
        }
