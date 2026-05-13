import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    premise_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_facts_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow_stage: Mapped[str] = mapped_column(String(50), default="init")
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(20), default="active")
    final_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    arguments: Mapped[List["Argument"]] = relationship(back_populates="session", lazy="selectin")
    opposing_responses: Mapped[List["OpposingResponse"]] = relationship(back_populates="session", lazy="selectin")
    judgments: Mapped[List["Judgment"]] = relationship(back_populates="session", lazy="selectin")
    hallucination_flags: Mapped[List["HallucinationFlag"]] = relationship(back_populates="session", lazy="selectin")

class Argument(Base):
    __tablename__ = "arguments"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    session: Mapped["Session"] = relationship(back_populates="arguments")
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    argument_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    hallucination_flags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class OpposingResponse(Base):
    __tablename__ = "opposing_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    session: Mapped["Session"] = relationship(back_populates="opposing_responses")
    argument_id: Mapped[Optional[int]] = mapped_column(ForeignKey("arguments.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Judgment(Base):
    __tablename__ = "judgments"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    session: Mapped["Session"] = relationship(back_populates="judgments")
    evaluation_json: Mapped[str] = mapped_column(Text)
    scores_json: Mapped[str] = mapped_column(Text)
    feedback_text: Mapped[str] = mapped_column(Text)
    final_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    terminated_properly: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class HallucinationFlag(Base):
    __tablename__ = "hallucination_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    session: Mapped["Session"] = relationship(back_populates="hallucination_flags")
    stage: Mapped[str] = mapped_column(String(50))
    detected_facts_json: Mapped[str] = mapped_column(Text, default="[]")
    warning_issued: Mapped[bool] = mapped_column(Boolean, default=True)
    score_penalty: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
