import logging
from typing import Any

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


def _collect_text_from_response(response: Any) -> str:
    """Prefer response.text; fall back to candidate parts if SDK blocks .text."""
    try:
        t = getattr(response, "text", None)
        if t is not None and str(t).strip():
            return str(t)
    except (ValueError, AttributeError) as e:
        logger.debug("response.text unavailable: %s", e)

    chunks: list[str] = []
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            txt = getattr(part, "text", None)
            if txt:
                chunks.append(str(txt))
    return "".join(chunks)


def _safety_settings() -> list[dict[str, Any]] | None:
    try:
        from google.generativeai.types import HarmBlockThreshold, HarmCategory

        return [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
        ]
    except (ImportError, AttributeError):
        return None


def call_gemini(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.2,
    top_p: float = 0.85,
    max_output_tokens: int = 2048,
) -> str:
    """
    Call Gemini with JSON shaped by the prompt only (no response_mime_type).
    Raises RuntimeError on missing key, blocks, or empty text.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key or not str(api_key).strip():
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to .env at the project root (Scenario_Analyzer/.env)."
        )

    genai.configure(api_key=api_key)
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
    combined = f"{system_prompt.strip()}\n\n{user_prompt.strip()}"

    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "top_p": top_p,
        "max_output_tokens": max_output_tokens,
    }

    safety = _safety_settings()
    model = genai.GenerativeModel(model_name)
    kwargs: dict[str, Any] = {"generation_config": generation_config}
    if safety:
        kwargs["safety_settings"] = safety

    response = model.generate_content(combined, **kwargs)
    text = _collect_text_from_response(response)
    if not text.strip():
        raise RuntimeError(
            "Empty Gemini response (no text). Possible safety block, model error, or quota issue."
        )
    return text
