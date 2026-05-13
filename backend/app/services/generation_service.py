"""High-level text generation orchestration."""

from __future__ import annotations

from app.core.config import settings
from app.core.model_manager import model_manager


class GenerationService:
    """Routes generation requests through the shared ModelManager."""

    def __init__(self) -> None:
        self.model = model_manager

    def generate_premise(
        self,
        topic: str,
        mode: str,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        self.model.set_adapter("premise")
        system_prompt = (
            "You generate realistic Indian property-law factual premises for legal training. "
            "Given a property-law topic and generation mode, write one fact-rich dispute scenario "
            "with parties, timeline, documents, possession facts, evidence gaps, and litigation ambiguity. "
            "Do not provide legal analysis, advice, issues, conclusions, or judgments."
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"Mode: {mode}\n"
            "Generate one realistic Indian property-law factual premise."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.model.generate(
            messages,
            max_new_tokens=max_new_tokens or settings.DEFAULT_MAX_NEW_TOKENS,
            temperature=temperature if temperature is not None else settings.DEFAULT_TEMPERATURE,
            top_p=top_p if top_p is not None else settings.DEFAULT_TOP_P,
            repetition_penalty=settings.DEFAULT_REPETITION_PENALTY,
        )

    def generate_opposing(
        self,
        user_argument: str,
        premise: str | None = None,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        self.model.set_adapter("opposing")
        system_prompt = (
            "You are adversarial Indian opposing counsel in a property-litigation training simulation. "
            "Critically challenge the user's argument using title analysis, possession analysis, civil procedure, "
            "evidentiary scrutiny, burden-of-proof evaluation, contradiction exposure, and fact-specific legal reasoning. "
            "Do not invent case citations."
        )
        if premise:
            user_content = f"Premise:\n{premise}\n\nUser Argument:\n{user_argument}"
        else:
            user_content = user_argument
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self.model.generate(
            messages,
            max_new_tokens=max_new_tokens or settings.DEFAULT_MAX_NEW_TOKENS,
            temperature=temperature if temperature is not None else settings.DEFAULT_TEMPERATURE,
            top_p=top_p if top_p is not None else settings.DEFAULT_TOP_P,
            repetition_penalty=settings.DEFAULT_REPETITION_PENALTY,
        )

    def generate_objection(
        self,
        user_argument: str,
        premise: str | None = None,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        self.model.set_adapter("objection")
        system_prompt = (
            "You are an Indian property-litigation argument evaluator for courtroom training. "
            "Given a user's legal argument, identify procedural objections, evidentiary weaknesses, "
            "burden-of-proof gaps, missing legal basis, contradictions, and areas for improvement. "
            "Stay within Indian property-law reasoning and do not invent case citations."
        )
        format_hint = (
            "Evaluate this argument. Provide: a brief summary, specific objections, evidentiary gaps, "
            "procedural issues, burden-of-proof problems, contradictions, improvement suggestions, "
            "and a strength score (0-100)."
        )
        if premise:
            user_content = (
                f"Premise:\n{premise}\n\nUser Argument:\n{user_argument}\n\n{format_hint}"
            )
        else:
            user_content = f"{user_argument}\n\n{format_hint}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self.model.generate(
            messages,
            max_new_tokens=max_new_tokens or 350,
            temperature=temperature if temperature is not None else 0.4,
            top_p=top_p if top_p is not None else 0.85,
            repetition_penalty=settings.DEFAULT_REPETITION_PENALTY,
        )


generation_service = GenerationService()
