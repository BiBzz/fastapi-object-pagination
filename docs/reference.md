---
description: "Reference of fastapi-object-pagination: the Page model and its fields, the paginate and paginate_related signatures, the previous and next URLs, the ORM enum and the errors."
---

# Reference

## Imports

| Module | Names |
| --- | --- |
| `fastapi_object_pagination` | `Page`, `ORM` |
| `fastapi_object_pagination.sqlmodel` | `paginate` |
| `fastapi_object_pagination.neontology` | `paginate`, `paginate_related` |

`fastapi_object_pagination` itself only needs Pydantic. Importing `fastapi_object_pagination.sqlmodel` or `fastapi_object_pagination.neontology` checks that the matching extra is installed.

## `Page`

```python
class Page(BaseModel, Generic[M]):
    items: list[M]
    item_count: int
    page_count: int
    current_page: int
    items_by_page: int
    previous_page_url: str | None
    next_page_url: str | None
```

`M` is any Pydantic model: a SQLModel table model, a Neontology node, or the model a serializer returns. Every field is required in the OpenAPI schema, the two URLs being nullable.

| Field | Value |
| --- | --- |
| `items` | the items of the page, at most `items_by_page` of them; empty past the last page |
| `item_count` | the number of items matching the filters, across all pages |
| `page_count` | `ceil(item_count / items_by_page)`, and `0` when `items_by_page` is `0` or less |
| `current_page` | the `current_page` argument, as given |
| `items_by_page` | the `items_by_page` argument, as given |
| `previous_page_url` | `None` when `current_page` is 1 or less, else `?current_page=<current_page - 1>&items_by_page=<items_by_page>` |
| `next_page_url` | `None` when `current_page` is `page_count` or more, else `?current_page=<current_page + 1>&items_by_page=<items_by_page>` |

The URLs are query strings, relative to the URL of the endpoint, and carry only these two parameters: name the query parameters of the endpoint `current_page` and `items_by_page` so that a client can follow them, and let it add its own filter parameters. Nothing is validated: a page past the end has no items and a previous URL that is past the end too, so declare the limits in FastAPI (`Query(ge=1)`), as on the [SQLModel page](sqlmodel.md).

## SQLModel

```python
async def paginate(
    model: type[M],
    async_session: AsyncSession,
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict[str, Any] | None = None,
    ordering: list[str] | None = None,
) -> Page[M]
```

From `fastapi_object_pagination.sqlmodel`. `AsyncSession` is `sqlmodel.ext.asyncio.session.AsyncSession`. Details on the [SQLModel page](sqlmodel.md).

## Neontology

```python
async def paginate(
    model: type[N],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: Filters | None = None,
    serializer: Callable[[N], M] | None = None,
) -> Page[N] | Page[M]

async def paginate_related(
    model: type[N],
    relationships: list[type[BaseRelationship]],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: Filters | None = None,
    ordering: list[str] | None = None,
    serializer: Callable[[N], M] | None = None,
) -> Page[N] | Page[M]
```

From `fastapi_object_pagination.neontology`. `N` is a Neontology `BaseNode` subclass, and `Filters` is `dict[tuple[type[BaseNode], str], Any]`. Overloads type the result: `Page[N]` without a serializer, `Page[M]` when `serializer` is passed, as a keyword argument. Details on the [Neontology page](neontology.md).

## `ORM`

```python
class ORM(str, Enum):
    NEONTOLOGY = "neontology"
    SQLMODEL = "sqlmodel"
```

The backends the library supports, named like their extras.

## Errors

| Raised | When |
| --- | --- |
| `ImportError` | importing a backend whose extra is not installed; the message gives the `uv add` command |
| `ValueError` | SQLModel: a filter on an unknown field, an unknown lookup, or an `in` value that is not a list, a tuple or a set |
| `AttributeError` | SQLModel: an ordering on an unknown field |
| `ValueError` | Neontology, `paginate_related`: a filter key that is not a `(BaseNode subclass, str)` tuple, or a relationship that is not a `BaseRelationship` subclass |

Errors of the database or of its driver reach the caller unchanged.
