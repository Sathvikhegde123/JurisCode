import re
import json
from typing import Dict
from app.models.db_models import Session
from app.services.fact_lock_service import FactLockService

class ContradictionService:
    def __init__(self, fls: FactLockService):
        self.fls = fls

    def check_argument(self, session: Session, argument_text: str) -> Dict:
        locked_facts = self.fls.get_locked_facts(session)
        locked_text = " ".join(locked_facts).lower()
        arg_lower = argument_text.lower()

        # Simple heuristic: check if years mentioned in argument are in locked facts
        locked_years = set(re.findall(r'\b(19|20)\d{2}\b', locked_text))
        arg_years = set(re.findall(r'\b(19|20)\d{2}\b', arg_lower))
        new_years = arg_years - locked_years

        violations = []
        if new_years:
            violations.append(f"Introduces new timeline references not in locked facts: {new_years}")

        # Note: In a real scenario, this would use a more sophisticated NLP check or LLM call.
        return {
            "has_contradictions": len(violations) > 0,
            "violations": violations,
            "new_facts_detected": len(violations) > 0,
            "requires_judge_review": True
        }
