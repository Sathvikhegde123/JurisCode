from typing import List, Dict, Any, Optional
from app.schemas.base import BaseSchema

class PremiseRequest(BaseSchema):
    topic: str
    mode: str

class PremiseResponse(BaseSchema):
    session_id: str
    premise: Dict[str, Any]
    locked_facts: List[str]
    workflow_stage: str
