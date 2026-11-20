from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_object_pagination import Page
from fastapi_object_pagination.sqlmodel import paginate


class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author: str
    year: int


engine = create_async_engine("sqlite+aiosqlite:///books.db")
app = FastAPI()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session


@app.get("/books")
async def list_books(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_page: Annotated[int, Query(ge=1)] = 1,
    items_by_page: Annotated[int, Query(ge=1, le=100)] = 10,
    author: str | None = None,
) -> Page[Book]:
    return await paginate(
        model=Book,
        async_session=session,
        current_page=current_page,
        items_by_page=items_by_page,
        filters={"author__iexact": author} if author else None,
        ordering=["-year", "title"],
    )
