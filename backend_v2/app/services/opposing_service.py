import json
from app.core.config import get_settings
from app.core.constants import WorkflowStage
from app.models.db_models import Session
from app.services.model_manager import ModelManager
from app.services.session_service import SessionService

class OpposingService:
    def __init__(self, mm: ModelManager, ss: SessionService):
        self.mm = mm
        self.ss = ss

    def _fallback_response(self, premise: dict, opening_text: str) -> str:
        topic = premise.get("title") or premise.get("scenario_text") or "the dispute"
        return (
            f"Opposing counsel response for {topic}:\n"
            "1. The argument overstates the record and should stay within the locked facts.\n"
            "2. The student must tie each legal conclusion to a specific document or fact.\n"
            "3. Burden, timeline, and possession issues should be addressed before any broad conclusion.\n"
            f"4. Response to the opening: {opening_text[:500] if opening_text else 'The opening lacks a concrete factual anchor.'}"
        )

    async def generate(self, session: Session):
        settings = get_settings()
        premise = json.loads(session.premise_json or "{}")
        facts = json.loads(session.locked_facts_json or "[]")
        arguments = await self.ss.get_arguments(session.id)
        opening = next((a for a in arguments if a.argument_type == "opening"), None)
        opening_text = opening.content if opening else ""

        raw = ""

        try:
            await self.mm.load_model("opposing", settings.resolved_opposing_path)

            prompt = (
                "You are an opposing counsel in an Indian property dispute mock trial.\n"
                "CASE PREMISE:\n"
                f"{json.dumps(premise, indent=2)}\n\n"
                "LOCKED FACTS (immutable record):\n"
                + "\n".join(f"- {f}" for f in facts) + "\n\n"
                "STUDENT OPENING ARGUMENT:\n"
                f"{opening_text}\n\n"
                "Instructions:\n"
                "- Challenge the argument adversarially using ONLY the locked facts above.\n"
                "- Do NOT invent new facts, case citations, or legal precedents not in the record.\n"
                "- Identify weaknesses in evidence, procedure, burden of proof, and logical contradictions.\n"
                "- Respond in structured oral argument style under 800 words."
            )

            messages = [{"role": "user", "content": prompt}]
            raw = await self.mm.generate_chat(messages, temperature=0.7, max_tokens=1536)
        except Exception:
            raw = self._fallback_response(premise, opening_text)
        finally:
            await self.mm.unload_model()

        opp = await self.ss.add_opposing_response(session.id, opening.id if opening else None, raw)

        return {
            "id": opp.id,
            "session_id": session.id,
            "content": raw,
            "workflow_stage": WorkflowStage.OPPOSING_RESPONSE.value,
        }
