from typing import List
from app.schemas.base import BaseSchema

class JudgmentResponse(BaseSchema):
    session_id: str
    burden_of_proof_analysis: str
    contradictions_found: List[str]
    evidentiary_sufficiency: str
    advocacy_score: int
    procedural_discipline: int
    hallucination_penalty: int
    educational_feedback: str
    termination_recommendation: str
    learning_points: List[str]
    final_score: int
    workflow_stage: str
