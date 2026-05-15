from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Full legal report JSON shape (Gemini + API full view)
FULL_REPORT_SCHEMA: dict[str, Any] = {
    "scenario_summary": "",
    "detected_domain": "",
    "issue_type": "",
    "simplified_explanation": "",
    "facts_identified": [],
    "missing_facts": [],
    "rights_possibly_involved": [],
    "possible_remedies": [],
    "possible_outcomes": [],
    "reasoning_trace": [],
    "source_pack_used": "",
    "official_sources_referenced": [],
    "source_grounding_status": "",
    "consult_lawyer_warning": False,
    "warning_reason": "",
    "confidence": "",
    "disclaimer": (
        "This is legal information for awareness and education, not legal advice."
    ),
}

# Backwards-compatible alias used across the codebase
RESPONSE_SCHEMA = FULL_REPORT_SCHEMA

COMPACT_VIEW_SCHEMA: dict[str, Any] = {
    "detected_issue": "",
    "short_summary": "",
    "main_points": [],
    "recommended_next_steps": [],
    "lawyer_warning": {"required": False, "reason": ""},
    "confidence": "",
    "disclaimer": FULL_REPORT_SCHEMA["disclaimer"],
}

CHAT_RESPONSE_SCHEMA: dict[str, Any] = {
    "assistant_message": "",
    "updated_understanding": [],
    "next_follow_up_questions": [],
    "recommended_next_steps": [],
    "lawyer_warning": {"required": False, "reason": ""},
    "disclaimer": FULL_REPORT_SCHEMA["disclaimer"],
}


class UserContext(BaseModel):
    state: str = Field(default="Unknown")
    language: str = Field(default="English")


class ScenarioAnalyzeRequest(BaseModel):
    scenario: str = Field(..., min_length=10)
    user_context: UserContext | None = None


class OfficialSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    act_name: str = ""
    section_reference: str = ""
    source_type: str = ""
    source_origin: str = ""
    relevance: str = ""
    verified: bool = False


class LawyerWarning(BaseModel):
    required: bool = False
    reason: str = ""


class CompactView(BaseModel):
    detected_issue: str
    short_summary: str
    main_points: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    lawyer_warning: LawyerWarning
    confidence: str = ""
    disclaimer: str = FULL_REPORT_SCHEMA["disclaimer"]


class ScenarioAnalyzeResponse(BaseModel):
    session_id: str
    """Selected source pack / classifier issue id (e.g. rera_delay)."""
    issue_type: str = ""
    compact_view: CompactView
    suggested_follow_up_questions: list[str] = Field(default_factory=list)
    full_report_available: bool = True
    full_report: dict[str, Any] | None = Field(
        default=None,
        description="Only returned in development when explicitly requested.",
    )


class FullReportResponse(BaseModel):
    session_id: str
    full_report: dict[str, Any]


class ScenarioChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)


class ScenarioChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    updated_understanding: list[str] = Field(default_factory=list)
    next_follow_up_questions: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    lawyer_warning: LawyerWarning
    disclaimer: str = FULL_REPORT_SCHEMA["disclaimer"]


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageResponse]


class SessionListItem(BaseModel):
    session_id: str
    original_scenario: str
    issue_type: str
    source_pack_used: str
    created_at: str


class SessionsListResponse(BaseModel):
    sessions: list[SessionListItem]


class SourcePacksListResponse(BaseModel):
    available_source_packs: list[str]


# --- Legal Clarity Score ---


class IssueUnderstandingSubScores(BaseModel):
    issue_category_detected: int = 0
    specific_sub_issue_detected: int = 0
    user_confirmed_or_refined_issue: int = 0


class FactClaritySubScores(BaseModel):
    ownership_or_history_clarified: int = 0
    timeline_clarified: int = 0
    possession_clarified: int = 0
    parties_or_legal_heirs_clarified: int = 0
    current_dispute_trigger_clarified: int = 0


class DocumentClaritySubScores(BaseModel):
    core_document_mentioned: int = 0
    mutation_or_revenue_record_mentioned: int = 0
    receipt_or_payment_proof_mentioned: int = 0
    notice_complaint_or_court_papers_mentioned: int = 0
    missing_documents_identified: int = 0


class RiskClaritySubScores(BaseModel):
    urgency_detected: int = 0
    possession_or_dispossession_risk_clarified: int = 0
    fraud_forgery_or_mutation_change_clarified: int = 0
    lawyer_police_or_court_trigger_clarified: int = 0


class IssueUnderstandingBreakdown(BaseModel):
    score: int = 0
    max_score: int = 25
    reason: str = ""
    sub_scores: IssueUnderstandingSubScores = Field(default_factory=IssueUnderstandingSubScores)


class FactClarityBreakdown(BaseModel):
    score: int = 0
    max_score: int = 30
    reason: str = ""
    sub_scores: FactClaritySubScores = Field(default_factory=FactClaritySubScores)


class DocumentClarityBreakdown(BaseModel):
    score: int = 0
    max_score: int = 25
    reason: str = ""
    sub_scores: DocumentClaritySubScores = Field(default_factory=DocumentClaritySubScores)


class RiskClarityBreakdown(BaseModel):
    score: int = 0
    max_score: int = 20
    reason: str = ""
    sub_scores: RiskClaritySubScores = Field(default_factory=RiskClaritySubScores)


class LegalClarityScoreBreakdown(BaseModel):
    issue_understanding: IssueUnderstandingBreakdown = Field(default_factory=IssueUnderstandingBreakdown)
    fact_clarity: FactClarityBreakdown = Field(default_factory=FactClarityBreakdown)
    document_clarity: DocumentClarityBreakdown = Field(default_factory=DocumentClarityBreakdown)
    risk_clarity: RiskClarityBreakdown = Field(default_factory=RiskClarityBreakdown)


class LegalClarityScoreResponse(BaseModel):
    session_id: str
    legal_clarity_score: int = 0
    clarity_level: str = ""
    score_breakdown: LegalClarityScoreBreakdown = Field(default_factory=LegalClarityScoreBreakdown)
    strengths: list[str] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    summary_feedback: str = ""
    teacher_explanation: str = (
        "This score measures how clearly the scenario was clarified through the conversation. "
        "It does not measure legal correctness or predict legal outcome."
    )


class ScoreNotYetGeneratedResponse(BaseModel):
    score_available: Literal[False] = False
    message: str = "Score has not been generated for this session yet."
