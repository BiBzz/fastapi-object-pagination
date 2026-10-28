from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    team: str


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        session.add_all(
            [
                Hero(name=f"hero-{index:02d}", team="preventers" if index % 2 else "zz")
                for index in range(25)
            ]
        )
        await session.commit()
        yield session
    await engine.dispose()
