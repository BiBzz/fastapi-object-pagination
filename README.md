# fastapi-object-pagination

Typed, async page objects for FastAPI, with one page shape for a SQL database
and for a graph database.

A FastAPI endpoint paginated with this library returns a `Page[Model]`: the
items, the counts, and the URLs of the previous and next pages. The same
`Page` comes back whether the data was read through
[SQLModel](https://sqlmodel.tiangolo.com/) or through
[Neontology](https://pypi.org/project/neontology/) (Neo4j and Memgraph), so the
clients of the API, and its OpenAPI schema, do not change when the storage
does.

## Why it exists

It was extracted from a production application that reads part of its data from
PostgreSQL and part of it from a Neo4j knowledge graph, and exposes both through
the same REST API. Existing FastAPI pagination libraries cover SQLAlchemy well
and graph stores not at all, so each backend ended up with its own page format
and the frontend had to special-case them. Pulling the page object out into a
library forced a single contract on both sides.

## Installation

Pick the backends you need, as extras:

```bash
uv add 'fastapi-object-pagination[sqlmodel]'
uv add 'fastapi-object-pagination[neontology]'
uv add 'fastapi-object-pagination[sqlmodel,neontology]'
```

or with pip:

```bash
pip install 'fastapi-object-pagination[sqlmodel]'
```

Importing a backend whose extra is missing raises `ImportError` with the command
to install it, rather than a bare `ModuleNotFoundError` from deep inside the
call stack.

## Usage

### SQLModel

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi_object_pagination import Page
from fastapi_object_pagination.sqlmodel import paginate
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

app = FastAPI()
engine = create_async_engine("postgresql+asyncpg://localhost/heroes")


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    team: str


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session


@app.get("/heroes")
async def list_heroes(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = 1,
    size: int = 10,
) -> Page[Hero]:
    return await paginate(
        model=Hero,
        async_session=session,
        current_page=page,
        items_by_page=size,
        filters={"team__icontains": "preventers"},
        ordering=["-name"],
    )
```

`paginate` is generic over the model, so the return type is inferred:
`paginate(model=Hero, ...)` is a `Page[Hero]`, and mypy checks the endpoint
signature against it.

### Neontology

```python
from fastapi import FastAPI
from fastapi_object_pagination import Page
from fastapi_object_pagination.neontology import paginate
from neontology import BaseNode

app = FastAPI()


class Person(BaseNode):
    __primarylabel__: str = "Person"
    __primaryproperty__: str = "name"

    name: str
    city: str


@app.get("/people")
async def list_people(page: int = 1, size: int = 10) -> Page[Person]:
    return await paginate(
        model=Person,
        current_page=page,
        items_by_page=size,
        filters={(Person, "city__iexact"): "Paris"},
    )
```

`paginate_related` does the same across a relationship, so a page of nodes can
be restricted to those connected to another label.

### The page

```json
{
  "items": [{"name": "Black Lion", "team": "Preventers"}],
  "item_count": 42,
  "page_count": 5,
  "current_page": 2,
  "items_by_page": 10,
  "previous_page_url": "?current_page=1&items_by_page=10",
  "next_page_url": "?current_page=3&items_by_page=10"
}
```

`Page` is a generic Pydantic model, so FastAPI documents the real item type in
the OpenAPI schema.

## Filters

Both backends take the same filter dictionary, with Django-style lookups:
`exact`, `iexact`, `contains`, `icontains`, `startswith`, `istartswith`,
`endswith`, `iendswith`, `gt`, `gte`, `lt`, `lte`, `in`, `isnull`. A key without
a lookup means `exact`.

SQLModel keys are field names (`"name__icontains"`). Neontology keys are
`(node_class, field_lookup)` tuples, because a Cypher query can touch several
labels at once.

On PostgreSQL the `in` lookup is compiled to `= ANY(ARRAY[...])` instead of
`IN (...)`, which plans better on large lists; other dialects keep `IN`.

## Compatibility

| | |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| Pydantic | 2.x |
| SQLModel | >= 0.0.25, with an async engine (`sqlmodel.ext.asyncio.session.AsyncSession`) |
| Neontology | >= 2.2.2 |

FastAPI itself is not a dependency: the library only returns Pydantic models,
so any FastAPI version that works with Pydantic 2 will serialize them.

## Licence

MIT. See [LICENSE](LICENSE).
