import json
from app.core.config import get_settings
from app.core.constants import WorkflowStage
from app.models.db_models import Session
from app.services.model_manager import ModelManager
from app.services.fact_lock_service import FactLockService
from app.services.session_service import SessionService

class PremiseService:
    def __init__(self, mm: ModelManager, fls: FactLockService, ss: SessionService):
        self.mm = mm
        self.fls = fls
        self.ss = ss

    def _fallback_premise(self, topic: str, mode: str) -> dict:
        scenario_text = (
            f"This is a mock-trial property dispute about {topic}. "
            f"The scenario is framed as a {mode} exercise for legal reasoning practice. "
            "Students should identify the facts, isolate the legal issues, and argue both sides using only the record."
        )
        return {
            "title": f"Mock Trial: {topic.title()}",
            "scenario_text": scenario_text,
            "parties": ["Plaintiff", "Defendant"],
            "property_description": f"Disputed property connected to {topic}.",
            "timeline": ["Initial dispute", "Document conflict", "Mock hearing preparation"],
            "key_documents": ["Sale deed", "Possession record", "Supporting correspondence"],
            "legal_issues": ["title", "possession", "evidence"],
            "facts": self.fls.extract_facts(scenario_text),
        }

    async def generate(self, session: Session, topic: str, mode: str):
        settings = get_settings()
        premise_data = None

        try:
            await self.mm.load_model("premise", settings.resolved_premise_path)

            prompt = (
                "You are an Indian property law premise generator for legal education.\n"
                f"Topic: {topic}\n"
                f"Mode: {mode}\n\n"
                "Generate a detailed, realistic Indian property litigation scenario. "
                "Include parties, property description, timeline, documents, and legal issues.\n\n"
                "Output STRICTLY as JSON with keys: "
                "title, scenario_text, parties, property_description, timeline, key_documents, legal_issues, facts (list of strings)."
            )

            messages = [{"role": "user", "content": prompt}]
            raw = await self.mm.generate_chat(messages, temperature=0.8, max_tokens=2048, stop=["```"])

            try:
                json_str = raw
                if "```json" in raw:
                    json_str = raw.split("```json")[1].split("```")[0]
                elif "```" in raw:
                    json_str = raw.split("```")[1].split("```")[0]
                premise_data = json.loads(json_str.strip())
            except Exception:
                premise_data = {"title": "Untitled Premise", "scenario_text": raw, "facts": []}
        except Exception:
            premise_data = self._fallback_premise(topic, mode)
        finally:
            await self.mm.unload_model()

        if premise_data is None:
            premise_data = self._fallback_premise(topic, mode)

        scenario_text = premise_data.get("scenario_text", "")

        if "facts" not in premise_data or not premise_data["facts"]:
            premise_data["facts"] = self.fls.extract_facts(scenario_text)

        locked = self.fls.lock_facts(session, scenario_text, premise_data.get("facts", []))

        session.topic = topic
        session.mode = mode
        session.premise_json = json.dumps(premise_data)
        session.workflow_stage = WorkflowStage.FACTS_LOCKED.value
        await self.ss.update(session)

        return {
            "session_id": session.id,
            "premise": premise_data,
            "locked_facts": locked,
            "workflow_stage": session.workflow_stage,
        }
