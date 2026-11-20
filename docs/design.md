---
description: "Design of fastapi-object-pagination: one page contract for SQL and graph data, typed entry points, optional backends, what it leaves out, and its known limitations."
---

# Design

fastapi-object-pagination is developed in the open. This page states what it aims at, how it builds a page, and what it leaves out today. Discussion happens in the [GitHub issues](https://github.com/BiBzz/fastapi-object-pagination/issues).

## Principles

1. **The page is the contract.** A client of the API sees one `Page` shape, whatever database answered: the storage can change behind an endpoint without changing its schema.
2. **Types first.** The item type flows from the model given to `paginate` to the `Page[...]` it returns, then to the OpenAPI schema.
3. **Pydantic, not FastAPI.** The library returns Pydantic models and imports nothing from FastAPI, so it follows FastAPI releases without a dependency on them.
4. **Pay for what you use.** Each backend is an extra; a missing one fails at import, with the command that installs it.
5. **One vocabulary.** The same lookups and the same ordering syntax on both backends, so that switching a resource from SQL to the graph changes the keys, not the habits.

## How a page is built

Every entry point sends two queries: one for the items of the page, with an offset of `(current_page - 1) * items_by_page` and a limit of `items_by_page`, and one for the number of matching items. The page count, the previous and the next URLs are computed from these numbers, without another query.

- **SQLModel**: `select(model)` with the filters and the ordering, then the same statement with `OFFSET` and `LIMIT`, and `SELECT count(*)` over it as a subquery. Both run on the `AsyncSession` the endpoint passes in.
- **Neontology, `paginate`**: Neontology's `get_count` and `match_nodes` on the model class.
- **Neontology, `paginate_related`**: a Cypher query written by the library, one `MATCH` per relationship, `RETURN DISTINCT` with `SKIP` and `LIMIT`, and `COUNT(DISTINCT ...)` for the count.

## Out of scope today

- **Cursor or keyset pagination.** Pages are addressed by number, with an offset: the simplest contract for a client, at the cost of the database skipping the rows before the page.
- **Synchronous sessions.** The SQLModel backend takes an `AsyncSession` only.
- **Other storages.** `ORM` names SQLModel and Neontology, and nothing else.
- **Filters in the URLs.** The previous and next URLs carry the page and its size; the endpoint and its clients own the filter parameters.

## Known limitations

As of version 0.1.1, read from the code:

- Neontology `paginate` forwards its `filters` to Neontology, which expects other keys than the declared ones: see the [Neontology page](neontology.md#filtering-a-single-label) for the way around it.
- Neontology queries run through the synchronous Neo4j driver, inside the coroutine.
- Neontology `paginate` has no `ordering`; `paginate_related` has.
- In `paginate_related`, two nodes of the same label share one Cypher variable, so a relationship between two nodes of the same label only matches a node related to itself.
- An unknown lookup raises `ValueError` on SQLModel, and is read as an equality on Neontology.

## Prior art

FastAPI pagination libraries cover SQLAlchemy well and graph stores not at all. fastapi-object-pagination was extracted from a production application that serves PostgreSQL and Neo4j data through the same REST API, where each backend had grown its own page format.
