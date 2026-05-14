"""SQLAlchemy models for scenario sessions, reports, and chat."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScenarioSession(Base):
    __tablename__ = "scenario_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    original_scenario: Mapped[str] = mapped_column(Text)
    user_state: Mapped[str] = mapped_column(String(128), default="Unknown")
    user_language: Mapped[str] = mapped_column(String(64), default="English")
    detected_domain: Mapped[str] = mapped_column(String(256), default="")
    issue_type: Mapped[str] = mapped_column(String(128), default="")
    source_pack_used: Mapped[str] = mapped_column(String(128), default="")
    confidence: Mapped[str] = mapped_column(String(32), default="")
    consult_lawyer_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    warning_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_grounding_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_debug_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ScenarioReport(Base):
    __tablename__ = "scenario_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    compact_view_json: Mapped[str] = mapped_column(Text, default="{}")
    full_report_json: Mapped[str] = mapped_column(Text, default="{}")
    suggested_follow_up_questions_json: Mapped[str] = mapped_column(Text, default="[]")
    official_sources_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    message_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
