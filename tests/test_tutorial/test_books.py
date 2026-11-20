import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from docs_src.books import app as books_app
from docs_src.books.app import Book
from fastapi_object_pagination.sqlmodel import paginate

pytestmark = pytest.mark.sqlmodel

RESPONSE = Path(books_app.__file__).with_name("response.json")


def make_books() -> list[Book]:
    return [
        Book(title="Sense and Sensibility", author="Jane Austen", year=1811),
        Book(title="Pride and Prejudice", author="Jane Austen", year=1813),
        Book(title="Mansfield Park", author="Jane Austen", year=1814),
        Book(title="Emma", author="Jane Austen", year=1815),
        Book(title="Persuasion", author="Jane Austen", year=1817),
        Book(title="Northanger Abbey", author="Jane Austen", year=1817),
        Book(title="Frankenstein", author="Mary Shelley", year=1818),
        Book(title="Dracula", author="Bram Stoker", year=1897),
    ]


@pytest_asyncio.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        session.add_all(make_books())
        await session.commit()
    monkeypatch.setattr(books_app, "engine", engine)
    transport = ASGITransport(app=books_app.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await engine.dispose()


async def test_the_documented_response(client: AsyncClient) -> None:
    response = await client.get(
        "/books",
        params={"author": "jane austen", "current_page": 2, "items_by_page": 2},
    )

    assert response.status_code == 200
    assert response.json() == json.loads(RESPONSE.read_text())


async def test_without_an_author_every_book_counts(client: AsyncClient) -> None:
    response = await client.get("/books")

    page = response.json()
    assert page["item_count"] == 8
    assert page["page_count"] == 1
    assert page["previous_page_url"] is None
    assert page["next_page_url"] is None
    assert [book["year"] for book in page["items"]][:3] == [1897, 1818, 1817]


async def test_page_and_size_are_validated(client: AsyncClient) -> None:
    first = await client.get("/books", params={"current_page": 0})
    too_large = await client.get("/books", params={"items_by_page": 101})

    assert first.status_code == 422
    assert too_large.status_code == 422


async def test_the_documented_filters_and_ordering(
    client: AsyncClient,
) -> None:
    engine = books_app.engine
    async with AsyncSession(engine) as session:
        page = await paginate(
            model=Book,
            async_session=session,
            filters={"author__iexact": "jane austen", "year__gte": 1814},
            ordering=["-year", "title"],
        )

    assert [book.title for book in page.items] == [
        "Northanger Abbey",
        "Persuasion",
        "Emma",
        "Mansfield Park",
    ]
    assert page.item_count == 4


def test_openapi_names_the_item_type() -> None:
    schema = books_app.app.openapi()
    page = schema["components"]["schemas"]["Page_Book_"]

    assert page["title"] == "Page[Book]"
    assert page["properties"]["items"]["items"] == {"$ref": "#/components/schemas/Book"}
