from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import field_validator
from app.schemas.base import BaseSchema

class ArgumentItem(BaseSchema):
    id: int
    argument_type: str
    round_number: int
    content: str
    created_at: datetime

class OpposingItem(BaseSchema):
    id: int
    content: str
    created_at: datetime

class JudgmentItem(BaseSchema):
    id: int
    final_score: Optional[int]
    feedback_text: str
    created_at: datetime

class HallucinationItem(BaseSchema):
    id: int
    stage: str
    score_penalty: int
    created_at: datetime

class SessionCreate(BaseSchema):
    topic: str
    mode: str

class SessionResponse(BaseSchema):
    id: str
    topic: Optional[str]
    mode: Optional[str]
    workflow_stage: str
    current_round: int
    max_rounds: int
    status: str
    final_score: Optional[int]
    created_at: datetime
    updated_at: datetime

class SessionDetail(SessionResponse):
    premise: Optional[Dict[str, Any]] = None
    locked_facts: List[str] = []
    arguments: List[ArgumentItem] = []
    opposing_responses: List[OpposingItem] = []
    judgments: List[JudgmentItem] = []
    hallucination_flags: List[HallucinationItem] = []

    @field_validator("premise", mode="before")
    @classmethod
    def parse_premise(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator("locked_facts", mode="before")
    @classmethod
    def parse_facts(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v or []
