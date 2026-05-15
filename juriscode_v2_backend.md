# JurisCode v2.0 — Complete Backend Architecture

> **Structured Procedural Legal Simulation Engine**
> 
> Indian property litigation education platform. Deterministic flow, single-model-in-memory GGUF inference, SQLite persistence, Groq judicial evaluation, and hallucination-resistant fact locking.

---

## Table of Contents

1. [Dependencies](#1-dependencies)
2. [Configuration](#2-configuration)
3. [Database Layer](#3-database-layer)
4. [Pydantic Schemas](#4-pydantic-schemas)
5. [Core Services](#5-core-services)
6. [API Layer](#6-api-layer)
7. [Application Entry](#7-application-entry)
8. [Migration & Setup Notes](#8-migration--setup-notes)
9. [Procedural Enforcement Summary](#9-procedural-enforcement-summary)

---

## 1. Dependencies

### `backend/requirements.txt`

```text
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0
asyncpg>=0.29.0
llama-cpp-python>=0.2.60
groq>=0.4.0
python-dotenv>=1.0.0
httpx>=0.27.0
```

---

## 2. Configuration

### `backend/.env.example`

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./juriscode.db

# GGUF Models (merged or base GGUFs; one loaded at a time)
PREMISE_GGUF_PATH=./local_models/premise.gguf
OPPOSING_GGUF_PATH=./local_models/opposing.gguf
MODEL_N_CTX=4096
MODEL_N_GPU_LAYERS=0

# Groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
GROQ_JUDGE_MODEL=llama-3.3-70b-versatile

# Workflow
MAX_ARGUMENT_ROUNDS=3
```

### `backend/app/core/config.py`

```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "JurisCode"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./juriscode.db"

    PREMISE_GGUF_PATH: str = "./local_models/premise.gguf"
    OPPOSING_GGUF_PATH: str = "./local_models/opposing.gguf"
    MODEL_N_CTX: int = 4096
    MODEL_N_GPU_LAYERS: int = 0

    GROQ_API_KEY: str = ""
    GROQ_JUDGE_MODEL: str = "llama-3.3-70b-versatile"
    MAX_ARGUMENT_ROUNDS: int = 3

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### `backend/app/core/constants.py`

```python
from enum import Enum

class WorkflowStage(str, Enum):
    INIT = "init"
    PREMISE_GENERATED = "premise_generated"
    FACTS_LOCKED = "facts_locked"
    STUDENT_OPENING = "student_opening"
    OPPOSING_RESPONSE = "opposing_response"
    STUDENT_REBUTTAL = "student_rebuttal"
    JUDGE_EVALUATION = "judge_evaluation"
    COMPLETED = "completed"

TOPICS = [
    "title dispute", "adverse possession", "partition suit",
    "coparcenary dispute", "forged sale deed", "mutation dispute",
    "boundary dispute", "encroachment", "inheritance dispute",
    "family settlement", "gift deed challenge", "tenant eviction",
    "builder possession delay", "RERA complaint", "specific performance",
    "injunction dispute", "landlord tenant conflict", "revenue record dispute",
    "fraudulent transfer", "easement rights"
]

GENERATION_MODES = [
    "clean law-school style hypotheticals",
    "messy real-world property disputes",
    "highly ambiguous ownership conflicts",
    "document-heavy evidentiary disputes",
    "family inheritance conflicts",
    "emotionally tense family property fights",
    "oral agreement disputes",
    "weak documentation cases",
    "contradictory timeline disputes",
    "tenant possession ambiguity disputes"
]
```

---

## 3. Database Layer

### `backend/app/db/base.py`

```python
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    pass

async def init_db():
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### `backend/app/db/session.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

### `backend/app/models/db_models.py`

```python
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
```

---

## 4. Pydantic Schemas

### `backend/app/schemas/base.py`

```python
from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

### `backend/app/schemas/session.py`

```python
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
```

### `backend/app/schemas/premise.py`

```python
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
```

### `backend/app/schemas/argument.py`

```python
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
```

### `backend/app/schemas/judgment.py`

```python
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
```

---

## 5. Core Services

### `backend/app/services/model_manager.py`

```python
import asyncio
import gc
import os
from typing import Optional, Any
from llama_cpp import Llama
from app.core.config import get_settings

class ModelManager:
    _instance: Optional["ModelManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._llm: Optional[Llama] = None
            cls._instance._active_model: Optional[str] = None
        return cls._instance

    @property
    def active_model(self) -> Optional[str]:
        return self._active_model

    async def load_model(self, model_key: str, gguf_path: str) -> Llama:
        async with self._lock:
            if self._active_model == model_key and self._llm is not None:
                return self._llm

            await self._unload()

            if not os.path.exists(gguf_path):
                raise FileNotFoundError(f"GGUF model not found: {gguf_path}")

            settings = get_settings()
            self._llm = Llama(
                model_path=gguf_path,
                n_ctx=settings.MODEL_N_CTX,
                n_gpu_layers=settings.MODEL_N_GPU_LAYERS,
                verbose=False,
            )
            self._active_model = model_key
            return self._llm

    async def unload_model(self) -> None:
        async with self._lock:
            await self._unload()

    async def _unload(self):
        if self._llm is not None:
            del self._llm
            self._llm = None
            self._active_model = None
            gc.collect()

    async def generate_chat(
        self,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Optional[list] = None,
        **kwargs: Any
    ) -> str:
        if self._llm is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        def _call():
            response = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or [],
                **kwargs
            )
            return response["choices"][0]["message"]["content"]

        return await asyncio.to_thread(_call)
```

### `backend/app/services/session_service.py`

```python
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.db_models import Session, Argument, OpposingResponse, Judgment
from app.core.constants import WorkflowStage

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, topic: str, mode: str) -> Session:
        s = Session(topic=topic, mode=mode, max_rounds=3)
        self.db.add(s)
        await self.db.commit()
        await self.db.refresh(s)
        return s

    async def get(self, session_id: str) -> Optional[Session]:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def get_detail(self, session_id: str) -> Optional[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.arguments),
                selectinload(Session.opposing_responses),
                selectinload(Session.judgments),
                selectinload(Session.hallucination_flags),
            )
        )
        return result.scalar_one_or_none()

    async def update(self, session: Session):
        session.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def get_arguments(self, session_id: str):
        result = await self.db.execute(
            select(Argument).where(Argument.session_id == session_id).order_by(Argument.created_at)
        )
        return result.scalars().all()

    async def add_argument(self, session: Session, arg_type: str, content: str, flags: dict):
        round_num = 1 if arg_type == "opening" else 2
        arg = Argument(
            session_id=session.id,
            argument_type=arg_type,
            round_number=round_num,
            content=content,
            hallucination_flags_json=__import__('json').dumps(flags),
        )
        self.db.add(arg)
        await self.db.commit()
        await self.db.refresh(arg)

        if flags.get("has_contradictions"):
            from app.models.db_models import HallucinationFlag
            hf = HallucinationFlag(
                session_id=session.id,
                stage=arg_type,
                detected_facts_json=__import__('json').dumps(flags.get("violations", [])),
                score_penalty=5 * len(flags.get("violations", [])),
            )
            self.db.add(hf)
            await self.db.commit()

        return arg

    async def add_opposing_response(self, session_id: str, argument_id: Optional[int], content: str) -> OpposingResponse:
        opp = OpposingResponse(session_id=session_id, argument_id=argument_id, content=content)
        self.db.add(opp)
        await self.db.commit()
        await self.db.refresh(opp)
        return opp

    async def add_judgment(self, session: Session, evaluation: dict, final_score: int):
        j = Judgment(
            session_id=session.id,
            evaluation_json=__import__('json').dumps(evaluation),
            scores_json=__import__('json').dumps({
                "advocacy_score": evaluation.get("advocacy_score", 0),
                "procedural_discipline": evaluation.get("procedural_discipline", 0),
                "hallucination_penalty": evaluation.get("hallucination_penalty", 0),
            }),
            feedback_text=evaluation.get("educational_feedback", ""),
            final_score=final_score,
        )
        self.db.add(j)
        await self.db.commit()
```

### `backend/app/services/workflow_service.py`

```python
from fastapi import HTTPException
from app.core.constants import WorkflowStage

class WorkflowService:
    _transitions = {
        WorkflowStage.INIT: [WorkflowStage.PREMISE_GENERATED],
        WorkflowStage.PREMISE_GENERATED: [WorkflowStage.FACTS_LOCKED],
        WorkflowStage.FACTS_LOCKED: [WorkflowStage.STUDENT_OPENING],
        WorkflowStage.STUDENT_OPENING: [WorkflowStage.OPPOSING_RESPONSE],
        WorkflowStage.OPPOSING_RESPONSE: [WorkflowStage.STUDENT_REBUTTAL],
        WorkflowStage.STUDENT_REBUTTAL: [WorkflowStage.JUDGE_EVALUATION],
        WorkflowStage.JUDGE_EVALUATION: [WorkflowStage.COMPLETED],
        WorkflowStage.COMPLETED: [],
    }

    def validate_transition(self, session, target: WorkflowStage):
        current = WorkflowStage(session.workflow_stage)
        if current == WorkflowStage.COMPLETED:
            raise HTTPException(status_code=400, detail="Proceedings have already terminated.")
        allowed = self._transitions.get(current, [])
        if target not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow transition: {current.value} -> {target.value}"
            )

    def validate_proceeding_active(self, session):
        if session.workflow_stage == WorkflowStage.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Proceedings are terminated. No further submissions allowed.")
```

### `backend/app/services/fact_lock_service.py`

```python
import re
import json
from typing import List, Optional
from app.models.db_models import Session

class FactLockService:
    def extract_facts(self, text: str) -> List[str]:
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
```

### `backend/app/services/contradiction_service.py`

```python
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

        locked_years = set(re.findall(r'(19|20)\d{2}', locked_text))
        arg_years = set(re.findall(r'(19|20)\d{2}', arg_lower))
        new_years = arg_years - locked_years

        violations = []
        if new_years:
            violations.append(f"Introduces new timeline references not in locked facts: {new_years}")

        return {
            "has_contradictions": len(violations) > 0,
            "violations": violations,
            "new_facts_detected": len(violations) > 0,
            "requires_judge_review": True
        }
```

### `backend/app/services/premise_service.py`

```python
import json
from app.core.config import get_settings
from app.core.constants import WorkflowStage
from app.models.db_models import Session
from app.services.model_manager import ModelManager
from app.services.fact_lock_service import FactLockService
from app.services.session_service import SessionService

class PremiseService:
    def __init__(self, mm: ModelManager, fls: FactLockService, ss: SessionService):
        self.mm = mm
        self.fls = fls
        self.ss = ss

    async def generate(self, session: Session, topic: str, mode: str):
        settings = get_settings()
        await self.mm.load_model("premise", settings.PREMISE_GGUF_PATH)

        prompt = (
            "You are an Indian property law premise generator for legal education.
"
            f"Topic: {topic}
"
            f"Mode: {mode}

"
            "Generate a detailed, realistic Indian property litigation scenario. "
            "Include parties, property description, timeline, documents, and legal issues.

"
            "Output STRICTLY as JSON with keys: "
            "title, scenario_text, parties, property_description, timeline, key_documents, legal_issues, facts (list of strings)."
        )

        messages = [{"role": "user", "content": prompt}]
        raw = await self.mm.generate_chat(messages, temperature=0.8, max_tokens=2048, stop=["```"])

        await self.mm.unload_model()

        try:
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]
            premise_data = json.loads(json_str.strip())
        except Exception:
            premise_data = {"title": "Untitled Premise", "scenario_text": raw, "facts": []}

        if "facts" not in premise_data or not premise_data["facts"]:
            premise_data["facts"] = self.fls.extract_facts(premise_data.get("scenario_text", raw))

        locked = self.fls.lock_facts(session, premise_data.get("scenario_text", raw), premise_data.get("facts", []))

        session.topic = topic
        session.mode = mode
        session.premise_json = json.dumps(premise_data)
        session.workflow_stage = WorkflowStage.FACTS_LOCKED.value
        await self.ss.update(session)

        return {
            "session_id": session.id,
            "premise": premise_data,
            "locked_facts": locked,
            "workflow_stage": session.workflow_stage,
        }
```

### `backend/app/services/opposing_service.py`

```python
import json
from app.core.config import get_settings
from app.core.constants import WorkflowStage
from app.models.db_models import Session
from app.services.model_manager import ModelManager
from app.services.session_service import SessionService

class OpposingService:
    def __init__(self, mm: ModelManager, ss: SessionService):
        self.mm = mm
        self.ss = ss

    async def generate(self, session: Session):
        settings = get_settings()
        await self.mm.load_model("opposing", settings.OPPOSING_GGUF_PATH)

        premise = json.loads(session.premise_json or "{}")
        facts = json.loads(session.locked_facts_json or "[]")
        arguments = await self.ss.get_arguments(session.id)
        opening = next((a for a in arguments if a.argument_type == "opening"), None)
        opening_text = opening.content if opening else ""

        prompt = (
            "You are an opposing counsel in an Indian property dispute mock trial.
"
            "CASE PREMISE:
"
            f"{json.dumps(premise, indent=2)}

"
            "LOCKED FACTS (immutable):
"
            + "
".join(f"- {f}" for f in facts) + "

"
            "STUDENT OPENING ARGUMENT:
"
            f"{opening_text}

"
            "Instructions:
"
            "- Challenge the argument adversarially using ONLY the locked facts above.
"
            "- Do NOT invent new facts, case citations, or legal precedents not in the record.
"
            "- Identify weaknesses in evidence, procedure, burden of proof, and logical contradictions.
"
            "- Respond in structured oral argument style under 800 words."
        )

        messages = [{"role": "user", "content": prompt}]
        raw = await self.mm.generate_chat(messages, temperature=0.7, max_tokens=1536)

        await self.mm.unload_model()

        opp = await self.ss.add_opposing_response(session.id, opening.id if opening else None, raw)

        return {
            "id": opp.id,
            "session_id": session.id,
            "content": raw,
            "workflow_stage": WorkflowStage.OPPOSING_RESPONSE.value,
        }
```

### `backend/app/services/judge_service.py`

```python
import json
import asyncio
from groq import Groq
from app.core.config import get_settings
from app.models.db_models import Session

class JudgeService:
    def __init__(self):
        settings = get_settings()
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured")
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_JUDGE_MODEL

    async def evaluate(self, session: Session):
        premise = json.loads(session.premise_json or "{}")
        facts = json.loads(session.locked_facts_json or "[]")

        opening = ""
        opposing = ""
        rebuttal = ""

        if hasattr(session, "arguments"):
            for arg in session.arguments:
                if arg.argument_type == "opening":
                    opening = arg.content
                elif arg.argument_type == "rebuttal":
                    rebuttal = arg.content

        if hasattr(session, "opposing_responses"):
            for opp in session.opposing_responses:
                opposing = opp.content

        prompt = (
            "You are a neutral Indian civil judge evaluating a mock property litigation simulation for educational purposes.

"
            "CASE PREMISE:
"
            f"{json.dumps(premise, indent=2)}

"
            "LOCKED FACTS (immutable record):
"
            + "
".join(f"- {f}" for f in facts) + "

"
            "STUDENT OPENING ARGUMENT:
"
            f"{opening}

"
            "OPPOSING COUNSEL RESPONSE:
"
            f"{opposing}

"
            "STUDENT REBUTTAL:
"
            f"{rebuttal}

"
            "Instructions:
"
            "- Evaluate burden of proof, contradictions, evidentiary sufficiency, advocacy quality, and procedural discipline.
"
            "- Do NOT invent facts outside the locked facts.
"
            "- Remain neutral and educational. Avoid dramatic language.
"
            "- Return STRICT JSON with keys:
"
            "  burden_of_proof_analysis (string),
"
            "  contradictions_found (list of strings),
"
            "  evidentiary_sufficiency (string),
"
            "  advocacy_score (0-100 int),
"
            "  procedural_discipline (0-100 int),
"
            "  hallucination_penalty (0-100 int, 0 if clean),
"
            "  educational_feedback (string),
"
            "  termination_recommendation (string, should say proceedings are terminated),
"
            "  learning_points (list of strings)"
        )

        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a neutral Indian civil judge. Evaluate mock litigation simulations. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

        response = await asyncio.to_thread(_call)
        content = response.choices[0].message.content
        result = json.loads(content)

        result.setdefault("advocacy_score", 0)
        result.setdefault("procedural_discipline", 0)
        result.setdefault("hallucination_penalty", 0)
        result.setdefault("contradictions_found", [])
        result.setdefault("learning_points", [])
        result.setdefault("termination_recommendation", "Proceedings are terminated.")

        return result
```

### `backend/app/services/scoring_service.py`

```python
from app.models.db_models import Session

class ScoringService:
    def compute_final_score(self, session: Session, judge_result: dict) -> int:
        base_advocacy = judge_result.get("advocacy_score", 0)
        base_procedural = judge_result.get("procedural_discipline", 0)
        hall_penalty = judge_result.get("hallucination_penalty", 0)

        flag_penalty = 0
        if hasattr(session, "hallucination_flags"):
            flag_penalty = sum(f.score_penalty for f in session.hallucination_flags)

        raw = int(0.5 * base_advocacy + 0.3 * base_procedural + 0.2 * (100 - hall_penalty))
        final = max(0, min(100, raw - flag_penalty))
        return final
```

---

## 6. API Layer

### `backend/app/api/deps.py`

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.model_manager import ModelManager
from app.services.workflow_service import WorkflowService
from app.services.fact_lock_service import FactLockService
from app.services.contradiction_service import ContradictionService
from app.services.session_service import SessionService

def get_model_manager():
    return ModelManager()

def get_workflow_service():
    return WorkflowService()

def get_fact_lock_service():
    return FactLockService()

def get_contradiction_service(fls: FactLockService = Depends(get_fact_lock_service)):
    return ContradictionService(fls)

def get_session_service(db: AsyncSession = Depends(get_db)):
    return SessionService(db)
```

### `backend/app/api/v1/endpoints/sessions.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_session_service
from app.schemas.session import SessionCreate, SessionResponse, SessionDetail
from app.services.session_service import SessionService

router = APIRouter()

@router.post("", response_model=SessionResponse)
async def create_session(
    req: SessionCreate,
    svc: SessionService = Depends(get_session_service),
):
    session = await svc.create(req.topic, req.mode)
    return session

@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
):
    session = await svc.get_detail(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
```

### `backend/app/api/v1/endpoints/premise.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_model_manager, get_fact_lock_service, get_session_service
from app.schemas.premise import PremiseRequest, PremiseResponse
from app.services.model_manager import ModelManager
from app.services.fact_lock_service import FactLockService
from app.services.session_service import SessionService
from app.services.premise_service import PremiseService
from app.services.workflow_service import WorkflowService
from app.core.constants import WorkflowStage

router = APIRouter()

@router.post("/{session_id}/premise", response_model=PremiseResponse)
async def generate_premise(
    session_id: str,
    req: PremiseRequest,
    mm: ModelManager = Depends(get_model_manager),
    fls: FactLockService = Depends(get_fact_lock_service),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    wf = WorkflowService()
    wf.validate_transition(session, WorkflowStage.PREMISE_GENERATED)

    ps = PremiseService(mm, fls, ss)
    return await ps.generate(session, req.topic, req.mode)
```

### `backend/app/api/v1/endpoints/argument.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import (
    get_model_manager, get_contradiction_service, get_session_service
)
from app.schemas.argument import (
    OpeningArgumentRequest, RebuttalRequest, ArgumentResponse, OpposingResponseSchema
)
from app.services.model_manager import ModelManager
from app.services.contradiction_service import ContradictionService
from app.services.session_service import SessionService
from app.services.opposing_service import OpposingService
from app.services.workflow_service import WorkflowService
from app.core.constants import WorkflowStage

router = APIRouter()

@router.post("/{session_id}/opening", response_model=ArgumentResponse)
async def submit_opening(
    session_id: str,
    req: OpeningArgumentRequest,
    cds: ContradictionService = Depends(get_contradiction_service),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.STUDENT_OPENING)

    flags = cds.check_argument(session, req.content)
    arg = await ss.add_argument(session, "opening", req.content, flags)

    session.workflow_stage = WorkflowStage.STUDENT_OPENING.value
    session.current_round = 1
    await ss.update(session)

    return {
        "id": arg.id,
        "session_id": session_id,
        "round_number": 1,
        "argument_type": "opening",
        "content": arg.content,
        "hallucination_flags": flags,
        "workflow_stage": session.workflow_stage,
    }

@router.post("/{session_id}/opposing", response_model=OpposingResponseSchema)
async def generate_opposing(
    session_id: str,
    mm: ModelManager = Depends(get_model_manager),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.OPPOSING_RESPONSE)

    osvc = OpposingService(mm, ss)
    result = await osvc.generate(session)

    session.workflow_stage = WorkflowStage.OPPOSING_RESPONSE.value
    await ss.update(session)

    return result

@router.post("/{session_id}/rebuttal", response_model=ArgumentResponse)
async def submit_rebuttal(
    session_id: str,
    req: RebuttalRequest,
    cds: ContradictionService = Depends(get_contradiction_service),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.STUDENT_REBUTTAL)

    flags = cds.check_argument(session, req.content)
    arg = await ss.add_argument(session, "rebuttal", req.content, flags)

    session.workflow_stage = WorkflowStage.STUDENT_REBUTTAL.value
    session.current_round = 2
    await ss.update(session)

    return {
        "id": arg.id,
        "session_id": session_id,
        "round_number": 2,
        "argument_type": "rebuttal",
        "content": arg.content,
        "hallucination_flags": flags,
        "workflow_stage": session.workflow_stage,
    }
```

### `backend/app/api/v1/endpoints/judgment.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_model_manager, get_session_service
from app.schemas.judgment import JudgmentResponse
from app.services.session_service import SessionService
from app.services.judge_service import JudgeService
from app.services.scoring_service import ScoringService
from app.services.workflow_service import WorkflowService
from app.services.model_manager import ModelManager
from app.core.config import get_settings
from app.core.constants import WorkflowStage

router = APIRouter()

@router.post("/{session_id}/judge", response_model=JudgmentResponse)
async def judge_evaluation(
    session_id: str,
    mm: ModelManager = Depends(get_model_manager),
    ss: SessionService = Depends(get_session_service),
):
    session = await ss.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    WorkflowService().validate_transition(session, WorkflowStage.JUDGE_EVALUATION)

    session = await ss.get_detail(session_id)

    jresult = await JudgeService().evaluate(session)
    final_score = ScoringService().compute_final_score(session, jresult)

    await ss.add_judgment(session, jresult, final_score)

    session.workflow_stage = WorkflowStage.JUDGE_EVALUATION.value
    session.status = "completed"
    session.final_score = final_score
    await ss.update(session)

    settings = get_settings()
    await mm.load_model("premise", settings.PREMISE_GGUF_PATH)

    return {
        "session_id": session_id,
        **jresult,
        "final_score": final_score,
        "workflow_stage": WorkflowStage.COMPLETED.value,
    }
```

### `backend/app/api/v1/router.py`

```python
from fastapi import APIRouter
from app.api.v1.endpoints import sessions, premise, argument, judgment

api_router = APIRouter()
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(premise.router, prefix="/sessions", tags=["premise"])
api_router.include_router(argument.router, prefix="/sessions", tags=["arguments"])
api_router.include_router(judgment.router, prefix="/sessions", tags=["judgment"])
```

---

## 7. Application Entry

### `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.db.base import init_db

app = FastAPI(
    title="JurisCode",
    version="2.0.0",
    description="Structured Procedural Legal Simulation Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    from app.services.model_manager import ModelManager
    mm = ModelManager()
    return {
        "status": "ok",
        "version": "2.0.0",
        "architecture": "procedural_simulation_engine",
        "active_model": mm.active_model,
    }
```

---

## 8. Migration & Setup Notes

1. **Export to GGUF**: Your current Qwen2.5-3B-Instruct + LoRA adapters must be merged and exported to GGUF using `llama.cpp` conversion scripts, or use `llama-cpp-python`'s LoRA apply if you prefer loading a base GGUF + LoRA at runtime. The `ModelManager` above assumes **merged GGUF files** for strict single-model-in-memory enforcement.
2. **Install**: `pip install -r requirements.txt`
3. **Env**: `cp .env.example .env` and fill `GROQ_API_KEY` and GGUF paths.
4. **Run**: `uvicorn app.main:app --reload`
5. **DB**: SQLite auto-creates on startup. To migrate to PostgreSQL later, simply change `DATABASE_URL` to `postgresql+asyncpg://user:pass@host/dbname`.

---

## 9. Procedural Enforcement Summary

| Rule | Implementation |
|------|----------------|
| **No infinite loops** | `WorkflowService` hardcodes a finite state machine. `COMPLETED` is terminal. |
| **Max rounds** | Implicit in the state machine: only 1 opening + 1 rebuttal allowed. `MAX_ARGUMENT_ROUNDS` is configurable but enforced by valid transitions. |
| **Fact locking** | `FactLockService` extracts and JSON-locks facts after premise generation. All downstream prompts reference `locked_facts`. |
| **Hallucination detection** | `ContradictionService` runs heuristic checks on every student submission. Flags are stored and score penalties applied. |
| **One model in memory** | `ModelManager` singleton loads/unloads per stage. After `/judge`, premise model reloads as idle default. |
| **Judge via Groq** | `JudgeService` calls Groq API with `response_format={"type": "json_object"}`. No local judge model. |
| **Session persistence** | `SessionService` + SQLAlchemy stores every stage, argument, response, judgment, and hallucination flag. |
