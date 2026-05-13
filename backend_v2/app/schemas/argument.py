from typing import List, Dict, Any
from app.schemas.base import BaseSchema

class OpeningArgumentRequest(BaseSchema):
    content: str

class RebuttalRequest(BaseSchema):
    content: str

class ArgumentResponse(BaseSchema):
    id: int
    session_id: str
    round_number: int
    argument_type: str
    content: str
    hallucination_flags: Dict[str, Any]
    workflow_stage: str

class OpposingResponseSchema(BaseSchema):
    id: int
    session_id: str
    content: str
    workflow_stage: str
