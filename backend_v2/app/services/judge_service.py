import json
import asyncio
from groq import Groq
from app.core.config import get_settings
from app.models.db_models import Session

class JudgeService:
    def __init__(self):
        settings = get_settings()
        if not settings.GROQ_API_KEY:
            # We allow it to be empty for now but it will fail during evaluate()
            pass
        self.client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        self.model = settings.GROQ_JUDGE_MODEL

    async def evaluate(self, session: Session):
        if not self.client:
            raise ValueError("GROQ_API_KEY not configured")

        premise = json.loads(session.premise_json or "{}")
        facts = json.loads(session.locked_facts_json or "[]")

        opening = ""
        opposing = ""
        rebuttal = ""

        if hasattr(session, "arguments"):
            for arg in session.arguments:
                if arg.argument_type == "opening":
                    opening = arg.content
                elif arg.argument_type == "rebuttal":
                    rebuttal = arg.content

        if hasattr(session, "opposing_responses"):
            for opp in session.opposing_responses:
                opposing = opp.content

        prompt = (
            "You are a neutral Indian civil judge evaluating a mock property litigation simulation for educational purposes.\n\n"
            "CASE PREMISE:\n"
            f"{json.dumps(premise, indent=2)}\n\n"
            "LOCKED FACTS (immutable record):\n"
            + "\n".join(f"- {f}" for f in facts) + "\n\n"
            "STUDENT OPENING ARGUMENT:\n"
            f"{opening}\n\n"
            "OPPOSING COUNSEL RESPONSE:\n"
            f"{opposing}\n\n"
            "STUDENT REBUTTAL:\n"
            f"{rebuttal}\n\n"
            "Instructions:\n"
            "- Evaluate burden of proof, contradictions, evidentiary sufficiency, advocacy quality, and procedural discipline.\n"
            "- Do NOT invent facts outside the locked facts.\n"
            "- Remain neutral and educational. Avoid dramatic language.\n"
            "- Return STRICT JSON with keys:\n"
            "  burden_of_proof_analysis (string),\n"
            "  contradictions_found (list of strings),\n"
            "  evidentiary_sufficiency (string),\n"
            "  advocacy_score (0-100 int),\n"
            "  procedural_discipline (0-100 int),\n"
            "  hallucination_penalty (0-100 int, 0 if clean),\n"
            "  educational_feedback (string),\n"
            "  termination_recommendation (string, should say proceedings are terminated),\n"
            "  learning_points (list of strings)"
        )

        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a neutral Indian civil judge. Evaluate mock litigation simulations. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

        response = await asyncio.to_thread(_call)
        content = response.choices[0].message.content
        result = json.loads(content)

        # Ensure all expected keys are present
        result.setdefault("advocacy_score", 0)
        result.setdefault("procedural_discipline", 0)
        result.setdefault("hallucination_penalty", 0)
        result.setdefault("contradictions_found", [])
        result.setdefault("learning_points", [])
        result.setdefault("termination_recommendation", "Proceedings are terminated.")

        return result
