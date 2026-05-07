from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.config import settings

# Since SQLite is our MVP DB, we replace `postgresql+asyncpg` with `sqlite+aiosqlite`
# if the URL is still pointing to the Postgres default and the user didn't change it.
db_url = settings.database_url
if "postgresql" in db_url and "localhost" in db_url:
    # MVP bypass: use SQLite by default unless properly configured
    db_url = "sqlite+aiosqlite:///flyingpig.db"

engine = create_async_engine(db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
