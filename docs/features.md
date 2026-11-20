---
description: "What fastapi-object-pagination does: one generic Page model, typed entry points for SQLModel and Neontology, Django style filters, ordering, previous and next URLs, and optional backends."
---

# Features

## One page, whatever the storage

It was extracted from a production application that reads part of its data from PostgreSQL and part of it from a Neo4j knowledge graph, and exposes both through the same REST API. FastAPI pagination libraries cover SQLAlchemy well and graph stores not at all, so each backend ended up with its own page format and the frontend had to special case them. Pulling the page object out into a library forced a single contract on both sides.

That contract is `Page`, a generic Pydantic model:

| Field | Type | Content |
| --- | --- | --- |
| `items` | `list[M]` | the items of the requested page |
| `item_count` | `int` | the number of items matching the filters, on every page |
| `page_count` | `int` | `item_count` divided by `items_by_page`, rounded up |
| `current_page` | `int` | the page that was asked for, starting at 1 |
| `items_by_page` | `int` | the page size that was asked for |
| `previous_page_url` | `str` or `None` | the query string of the previous page, `None` on the first page |
| `next_page_url` | `str` or `None` | the query string of the next page, `None` on the last page |

The [reference](reference.md) gives the exact rules for each field.

## Typed from the call to the schema

Each entry point is generic over the model it reads:

- `paginate(model=Book, ...)` from `fastapi_object_pagination.sqlmodel` returns a `Page[Book]`;
- `paginate(model=Person, ...)` and `paginate_related(model=Person, ...)` from `fastapi_object_pagination.neontology` return a `Page[Person]`;
- with `serializer=to_person_out`, the same Neontology calls return a `Page[PersonOut]`, the type the serializer returns.

The package ships its type information (`py.typed`), so mypy checks the value an endpoint returns against its declared `Page[...]`, and FastAPI turns that declaration into an OpenAPI schema named after the item type (`Page_Book_`), with `items` typed as `Book`.

## Two backends, one vocabulary

| | SQLModel | Neontology |
| --- | --- | --- |
| Import | `fastapi_object_pagination.sqlmodel` | `fastapi_object_pagination.neontology` |
| Entry points | `paginate` | `paginate`, `paginate_related` |
| Runs on | an `AsyncSession` you pass in | the Neontology connection of the application |
| Filter keys | `"field__lookup"` | `(NodeClass, "field__lookup")` |
| Ordering | `paginate` | `paginate_related` |
| Serializer | no | both entry points |

The [SQLModel](sqlmodel.md) and [Neontology](neontology.md) pages show each backend in an application.

## Django style filters

Both backends take the same lookups, written after a double underscore: `exact`, `iexact`, `contains`, `icontains`, `startswith`, `istartswith`, `endswith`, `iendswith`, `gt`, `gte`, `lt`, `lte`, `in` and `isnull`. A key without a lookup means `exact`. Every filter narrows the count as well as the items, and several filters are combined with `AND`.

SQLModel keys are field names (`"author__iexact"`). Neontology keys are `(node_class, field_lookup)` tuples, because a Cypher query can match several labels at once and filter on any of them.

On PostgreSQL, the `in` lookup compiles to `= ANY(...)`, with the whole list bound as one array parameter, instead of `IN (...)`, which plans better on long lists. Other dialects keep `IN`.

The [filters](filters.md) page gives the SQL and the Cypher each lookup becomes.

## Ordering

`ordering` is a list of field names, applied in order, each one descending when it starts with `-`: `["-year", "title"]` sorts the most recent books first, and books of the same year by title.

## Pages across relationships

`paginate_related` pages the nodes of one label that take part in a list of relationships, and filters on any label those relationships reach: the employees of a company, the people living in a city. It counts and returns each node once, however many relationships match it.

## Serializers

A Neontology page can carry an API model rather than the node that was queried: pass `serializer`, a function from the node to a Pydantic model, and each item is converted before the page is built. The counts and the URLs do not change, and the page is typed on what the serializer returns.

## Optional backends

Pydantic is the only required dependency. Each backend is an extra, `sqlmodel` or `neontology`, and importing a backend whose extra is missing fails at once with the command that installs it:

```text
ImportError: ORM 'neontology' needs extra dependencies. Please run: uv add 'fastapi-object-pagination[neontology]'
```

rather than with a bare `ModuleNotFoundError` from deep inside the call stack. The `sqlmodel` extra also installs `sqlalchemy[asyncio]`, which brings the `greenlet` package an `AsyncSession` cannot run without.

## Compatibility

| | |
| --- | --- |
| Python | 3.11, 3.12, 3.13 |
| Pydantic | 2.x |
| SQLModel | 0.0.25 or later, with an async engine |
| Neontology | 2.2.2 or later |

The test suite runs on each of these Python versions.
