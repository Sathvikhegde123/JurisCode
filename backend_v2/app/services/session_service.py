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
