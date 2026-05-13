from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    pass

async def init_db():
    from app.db.session import engine
    from app.models.db_models import Session, Argument, OpposingResponse, Judgment, HallucinationFlag # ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
