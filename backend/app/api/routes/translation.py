from fastapi import APIRouter, HTTPException

from app.schemas.health import TranslationRequest
from app.services.ai_service import AIService, AIServiceError

router = APIRouter(prefix="/api", tags=["language"])


@router.post("/translate")
async def translate_health_content(payload: TranslationRequest):
    try:
        result = await AIService().translate_health_content(payload.content, payload.language)
    except AIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        **result,
        "language": payload.language,
        "review_required": True,
        "safety_note": "Machine translation can be inaccurate. Verify medical instructions with a qualified interpreter or clinician.",
    }
