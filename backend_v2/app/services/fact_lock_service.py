import re
import json
from typing import List, Optional
from app.models.db_models import Session

class FactLockService:
    def extract_facts(self, text: str) -> List[str]:
        # Split into sentences and filter short ones
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 15]

    def lock_facts(self, session: Session, scenario_text: str, explicit_facts: Optional[List[str]] = None) -> List[str]:
        facts = explicit_facts if explicit_facts else self.extract_facts(scenario_text)
        session.locked_facts_json = json.dumps(facts)
        return facts

    def get_locked_facts(self, session: Session) -> List[str]:
        if not session.locked_facts_json:
            return []
        return json.loads(session.locked_facts_json)
