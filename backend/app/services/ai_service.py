from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings
from app.services.ocr_service import OCRService


class AIServiceError(RuntimeError):
    pass


class AIService:
    SAFETY_INSTRUCTION = (
        "You are an informational health assistant, not a doctor or therapist. Never diagnose, prescribe, "
        "infer undocumented medical facts, or invent records, results, or medicines. Use only supplied evidence. "
        "For image tasks, do not claim definitive diagnosis, exact wound depth, or rabies diagnosis. "
        "If uncertain, say so. For urgent symptoms, recommend immediate local emergency care. "
        "Respond as a JSON object with the task-appropriate fields only."
    )

    def __init__(self) -> None:
        self.base_url = settings.omniroute_base_url.rstrip("/")
        self.api_key = settings.omniroute_api_key
        self.model = settings.omniroute_model

    @property
    def configured(self) -> bool:
        return bool(
            self.base_url
            and self.api_key
            and self.api_key not in {"demo-key", "replace-me"}
            and self.model
        )

    def _local_response(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if method == "answer_health_question":
            context = payload.get("context") or []
            if payload.get("response_language") == "hi":
                answer = (
                    "आपके दिए गए स्वास्थ्य रिकॉर्ड में इस प्रश्न से संबंधित जानकारी नहीं मिली।"
                    if not context
                    else "दिए गए रिकॉर्ड में संबंधित प्रविष्टियाँ मिलीं। नीचे दिए गए साक्ष्य देखें; OmniRoute कॉन्फ़िगर न होने तक AI व्याख्या उपलब्ध नहीं है।"
                )
                return {"answer": answer, "basis": "records", "evidence": context[:5], "ai_status": "unavailable"}
            if not context:
                answer = "I couldn't find information relevant to that question in the health records provided."
            else:
                answer = (
                    "I found related entries in the records provided. Review the evidence items below; "
                    "AI interpretation is unavailable until OmniRoute is configured."
                )
            return {"answer": answer, "basis": "records", "evidence": context[:5], "ai_status": "unavailable"}
        if method == "extract_medical_record":
            tests = OCRService.extract_lab_candidates(str(payload.get("text", "")))
            return {
                "tests": tests,
                "summary": (
                    f"Text extraction found {len(tests)} possible lab value(s). Verify the extracted values against the report."
                    if tests
                    else "No recognized laboratory values were found in the extracted text. Verify the report manually."
                ),
                "ai_status": "unavailable",
            }
        if method == "summarize_document":
            return {
                "summary": "AI explanation is unavailable. The extracted text is shown for review; consult the document or a clinician.",
                "ai_status": "unavailable",
            }
        if method == "analyze_medical_text":
            return {"summary": "Automated medical interpretation is unavailable; extracted text requires review.", "ai_status": "unavailable"}
        if method == "explain_lab_result":
            return {"explanation": "AI explanation is unavailable. Compare the result with the reference range printed by the laboratory.", "ai_status": "unavailable"}
        if method in {"analyze_injury", "analyze_animal_bite"}:
            return {
                "urgency": "Unable to assess remotely",
                "findings": "This service cannot reliably assess an injury from the information or image provided.",
                "first_aid": "For a wound, gently rinse with clean running water and cover with a clean dressing. Do not delay emergency care for severe bleeding or a serious injury.",
                "warning_signs": "Seek urgent care for uncontrolled bleeding, severe pain, loss of sensation or movement, difficulty breathing, confusion, or rapidly worsening symptoms.",
                "ai_status": "unavailable",
            }
        if method == "recognize_medicine":
            return {"identified": False, "warning": "Medicine recognition is unavailable. Do not take a medicine based on an image; verify it with a pharmacist or clinician.", "ai_status": "unavailable"}
        if method == "recognize_animal":
            return {"identified": False, "warning": "Animal recognition is unavailable. Do not approach an animal to identify it.", "ai_status": "unavailable"}
        if method == "generate_doctor_summary":
            return {"summary": "AI summary generation is unavailable. Review your saved records and bring the originals to your clinician.", "clinical_notes": [], "ai_status": "unavailable"}
        if method == "wellbeing_response":
            if payload.get("language") == "hi":
                return {
                    "response": "अपनी बात साझा करने के लिए धन्यवाद। मैं सामान्य सुझाव दे सकता हूँ, लेकिन चिकित्सक या थेरेपिस्ट नहीं हूँ। यदि आप तत्काल खतरे में हैं, तो स्थानीय आपातकालीन सेवा या किसी भरोसेमंद व्यक्ति से अभी संपर्क करें।",
                    "activities": ["यदि आपको ठीक लगे, तो आराम से धीरे-धीरे साँस लेने का अभ्यास करें।", "किसी भरोसेमंद व्यक्ति से बात करने पर विचार करें।"],
                    "ai_status": "unavailable",
                }
            return {
                "response": "Thank you for sharing. I can listen and offer general coping ideas, but I am not a therapist. If you may be in immediate danger, contact local emergency services or someone you trust now.",
                "activities": ["Try a comfortable, slow breathing pattern if that feels safe for you.", "Consider contacting a trusted person."],
                "ai_status": "unavailable",
            }
        if method == "translate_health_content":
            raise AIServiceError("Translation is unavailable until OmniRoute is configured.")
        return {"status": "unavailable", "message": "OmniRoute AI is not configured."}

    async def _call_omni(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return self._local_response(method, payload)

        user_content: Any = json.dumps({"task": method, "input": payload}, ensure_ascii=False)
        image_data_url = payload.get("image_data_url")
        if image_data_url:
            sanitized_payload = {key: value for key, value in payload.items() if key != "image_data_url"}
            user_content = [
                {
                    "type": "text",
                    "text": json.dumps({"task": method, "input": sanitized_payload}, ensure_ascii=False),
                },
                {"type": "image_url", "image_url": {"url": image_data_url, "detail": "low"}},
            ]
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": self.SAFETY_INSTRUCTION
                                + (" Respond in Hindi." if payload.get("response_language") == "hi" or payload.get("language") == "hi" else ""),
                            },
                            {"role": "user", "content": user_content},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIServiceError("The OmniRoute request failed. Check the service configuration and try again.") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("Unexpected model response content")
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIServiceError("OmniRoute returned an invalid structured response.") from exc
        if not isinstance(result, dict):
            raise AIServiceError("OmniRoute returned an invalid structured response.")
        return result

    async def analyze_medical_text(self, text: str):
        return await self._call_omni("analyze_medical_text", {"text": text})

    async def extract_medical_record(self, text: str):
        return await self._call_omni("extract_medical_record", {"text": text})

    async def explain_lab_result(self, lab_result: dict[str, Any]):
        return await self._call_omni("explain_lab_result", {"lab_result": lab_result})

    async def summarize_document(self, text: str):
        return await self._call_omni("summarize_document", {"text": text})

    async def answer_health_question(self, question: str, context: list[dict[str, Any]], response_language: str = "en"):
        return await self._call_omni(
            "answer_health_question",
            {"question": question, "context": context, "response_language": response_language},
        )

    async def analyze_injury(self, payload: dict[str, Any]):
        return await self._call_omni("analyze_injury", payload)

    async def analyze_animal_bite(self, payload: dict[str, Any]):
        return await self._call_omni("analyze_animal_bite", payload)

    async def recognize_animal(self, payload: dict[str, Any]):
        return await self._call_omni("recognize_animal", payload)

    async def recognize_medicine(self, payload: dict[str, Any]):
        return await self._call_omni("recognize_medicine", payload)

    async def generate_doctor_summary(self, payload: dict[str, Any]):
        return await self._call_omni("generate_doctor_summary", payload)

    async def wellbeing_response(self, payload: dict[str, Any]):
        return await self._call_omni("wellbeing_response", payload)

    async def translate_health_content(self, content: str, language: str):
        return await self._call_omni("translate_health_content", {"content": content, "language": language})
