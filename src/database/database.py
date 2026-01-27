from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import settings
from src.database.model import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# initialize database
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# get database session
@asynccontextmanager
async def with_get_db():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


async def fastapi_get_db():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
