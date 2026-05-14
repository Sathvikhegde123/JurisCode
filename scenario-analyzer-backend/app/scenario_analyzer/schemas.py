from typing import Any

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
