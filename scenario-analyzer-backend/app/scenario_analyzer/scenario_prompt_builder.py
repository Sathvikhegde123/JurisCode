import json
from typing import Any


def build_scenario_prompt(
    scenario: str,
    user_context: dict[str, Any],
    source_pack: dict[str, Any],
    response_schema: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """You are a legal literacy assistant for Indian citizens.

You explain legal situations in simple educational language.

You must not provide final legal advice.
You must not guarantee outcomes.
You must not say who will win or lose.
You must not invent statutes, sections, citations, case names, or legal provisions.
Use only the provided source pack as legal grounding.
If the source pack is limited, say that source grounding is limited.
Always list missing facts.
Always include disclaimer.
Return only valid JSON matching the required schema.
Do not include markdown.
Do not include text outside JSON."""

    pack_for_prompt = {
        k: v
        for k, v in source_pack.items()
        if not str(k).startswith("_")
    }

    user_payload = {
        "user_scenario": scenario,
        "user_context": user_context,
        "selected_source_pack": pack_for_prompt,
        "required_response_schema": response_schema,
        "output_rules": [
            "Return only valid JSON.",
            "Use simple citizen-friendly language.",
            "Do not provide final legal advice.",
            "Do not invent sections or citations.",
            "Use source_pack_used exactly as the selected source pack issue_type.",
            "official_sources_referenced must come only from selected_source_pack.official_sources.",
            (
                "source_grounding_status should mention that curated official statutory summary "
                "was used and exact section-level verification is pending."
            ),
            "scenario_summary must be at least 18 words and must paraphrase concrete facts from user_scenario.",
            "Never use the vague phrase 'property-related legal issue' as the entire scenario_summary.",
            "simplified_explanation must be at least 18 words and scenario-specific, not a generic system apology.",
            "If facts are thin, still tie sentences to what the user wrote (parties, property type, timeline).",
            "missing_facts should name real categories (documents, notices, possession, payments), not filler.",
        ],
    }

    user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)
    return system_prompt, user_prompt
