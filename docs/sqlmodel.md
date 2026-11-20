---
description: "Paginate a SQLModel table in a FastAPI endpoint with fastapi-object-pagination: an AsyncSession, filters, ordering and a typed Page."
---

# SQLModel

The SQLModel backend pages a table model over an async session, with one query for the items and one for the count.

## Install

```console
$ pip install 'fastapi-object-pagination[sqlmodel]'
```

The extra installs SQLModel and `sqlalchemy[asyncio]`. Add the async driver of your database: `asyncpg` for PostgreSQL, `aiosqlite` for SQLite.

## An endpoint

```python hl_lines="9  10  29-43"
--8<-- "docs_src/books/app.py"
```

- `Book` is an ordinary SQLModel table model: the page carries it as it is.
- `get_session` opens an `AsyncSession` per request, as in the SQLModel tutorial; `paginate` only reads through it and leaves it open, so the endpoint can keep using it.
- `current_page` and `items_by_page` are validated by FastAPI (`Query(ge=1)`): the library uses the values it is given as they are, and a page past the end comes back with no items.
- `filters` is `None` when no author is given, which reads every book.

With six books by Jane Austen in the table, `GET /books?author=jane austen&current_page=2&items_by_page=2` returns:

```json
--8<-- "docs_src/books/response.json"
```

The previous and next URLs carry `current_page` and `items_by_page`, not the `author` filter: a client that follows them keeps its own filter parameters.

## The call

```python
await paginate(
    model=Book,
    async_session=session,
    current_page=1,
    items_by_page=10,
    filters=None,
    ordering=None,
)
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `model` | | the SQLModel table model to read, and the type of the items |
| `async_session` | | an open `sqlmodel.ext.asyncio.session.AsyncSession` |
| `current_page` | `1` | the page to return, starting at 1 |
| `items_by_page` | `10` | the size of a page |
| `filters` | `None` | a dictionary of `"field__lookup": value` filters, see [filters](filters.md) |
| `ordering` | `None` | a list of field names, each descending when it starts with `-` |

## What it runs

`paginate` builds `select(Book)`, adds a `WHERE` clause for the filters and an `ORDER BY` for the ordering, then sends two queries on the session:

1. the items: the same statement with `OFFSET (current_page - 1) * items_by_page` and `LIMIT items_by_page`;
2. the count: `SELECT count(*)` over the statement as a subquery, so the filters narrow the count too.

## Filters and ordering

```python
page = await paginate(
    model=Book,
    async_session=session,
    filters={"author__iexact": "jane austen", "year__gte": 1814},
    ordering=["-year", "title"],
)
```

`page.items` holds the four books by Jane Austen published in 1814 or later, the most recent first, and `page.item_count` is 4.

Keys are field names of the model, followed by a lookup. The [filters](filters.md) page lists the lookups and the SQL each one becomes.

Errors are raised before any query is sent:

- a filter on a field the model does not have raises `ValueError` (`Attribute 'nickname' not found in Book`);
- an unknown lookup raises `ValueError` (`Unknown lookup: sounds_like`);
- an `in` filter whose value is not a list, a tuple or a set raises `ValueError`;
- an ordering on a field the model does not have raises `AttributeError`.

A FastAPI endpoint that builds its filters from user input should therefore choose the field names itself, as `list_books` does with `author`.

## PostgreSQL

On a PostgreSQL session, `{"id__in": [1, 2, 3]}` compiles to `book.id = ANY(%(param_1)s)`, the list bound as a single array parameter, instead of `book.id IN (...)` with one parameter per value, which plans better on long lists. The dialect is read from the session, nothing has to be configured. An empty list matches no row, on every dialect.
