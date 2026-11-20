---
description: "fastapi-object-pagination: typed, async page objects for FastAPI, with the same Page shape whether the data comes from SQLModel or from a Neontology graph (Neo4j, Memgraph)."
---

<style>
.md-content .md-typeset h1 { display: none; }
</style>

# fastapi-object-pagination

<p align="center">
  <a href="https://fastapi-object-pagination.businessagile.eu"><img src="img/logo.svg" alt="fastapi-object-pagination" width="560"></a>
</p>
<p align="center">
    <em>fastapi-object-pagination, typed async pages for FastAPI, from a SQL or a graph database.</em>
</p>
<p align="center">
<a href="https://github.com/BiBzz/fastapi-object-pagination/blob/development/LICENSE" target="_blank"><img src="img/badges/license.svg" alt="License: MIT"></a>
<img src="img/badges/status.svg" alt="Status: beta">
<img src="img/badges/python.svg" alt="Python 3.11+">
</p>

---

**Documentation**: <a href="https://fastapi-object-pagination.businessagile.eu" target="_blank">https://fastapi-object-pagination.businessagile.eu</a>

**Source Code**: <a href="https://github.com/BiBzz/fastapi-object-pagination" target="_blank">https://github.com/BiBzz/fastapi-object-pagination</a>

**Created by**: <a href="https://businessagile.eu/en/about" target="_blank">Alexandre BERREBI</a>, maintained by <a href="https://businessagile.eu" target="_blank">Business Agile</a>

---

fastapi-object-pagination paginates a **FastAPI** endpoint and returns a `Page[Model]`: the items, the counts, and the URLs of the previous and next pages. The same `Page` comes back whether the data was read through <a href="https://sqlmodel.tiangolo.com" target="_blank">SQLModel</a> or through <a href="https://pypi.org/project/neontology/" target="_blank">Neontology</a> (Neo4j and Memgraph), so the clients of the API, and its OpenAPI schema, do not change when the storage does.

The key features are:

* **One page shape**: `Page` is a generic Pydantic model. A page of SQL rows and a page of graph nodes have the same fields and the same JSON.
* **Typed**: `paginate(model=Book, ...)` returns a `Page[Book]`, so mypy checks the endpoint signature, and FastAPI documents the real item type in the OpenAPI schema.
* **Async**: the SQLModel backend runs on an `AsyncSession`, and every entry point is a coroutine you `await` in an `async def` endpoint.
* **Django style filters**: `{"author__iexact": "jane austen"}` for SQLModel, `{(Company, "name__iexact"): "acme"}` for Neontology, with the same fourteen lookups on both sides.
* **Ordering**: `["-year", "title"]`, a minus sign for descending.
* **Across relationships**: `paginate_related` pages the nodes connected to another label, and filters on that label.
* **Serializers**: a Neontology page can carry an API model built from each node instead of the node itself, and is typed on it.
* **Light**: Pydantic is the only required dependency. Each backend is an extra, and importing one whose extra is missing tells you the command that installs it.

## Requirements

A recent and currently supported <a href="https://www.python.org/downloads/" target="_blank">version of Python</a>: 3.11 or later.

<a href="https://docs.pydantic.dev" target="_blank">Pydantic</a> 2, installed with the library. FastAPI itself is not a dependency: the library returns Pydantic models, which any FastAPI version working with Pydantic 2 serializes.

And one of the backends:

* **SQLModel** 0.0.25 or later, with an async engine (`sqlmodel.ext.asyncio.session.AsyncSession`).
* **Neontology** 2.2.2 or later, connected to Neo4j or Memgraph.

## Installation

Pick the backends you need, as extras:

```console
$ pip install 'fastapi-object-pagination[sqlmodel]'
---> 100%
```

or with uv:

```console
$ uv add 'fastapi-object-pagination[sqlmodel]'
$ uv add 'fastapi-object-pagination[neontology]'
$ uv add 'fastapi-object-pagination[sqlmodel,neontology]'
```

## Example

### A paginated endpoint

A table of books, read through SQLModel, and an endpoint that returns them a page at a time, filtered by author and ordered from the most recent:

```python hl_lines="9  10  36-43"
--8<-- "docs_src/books/app.py"
```

`paginate` is generic over the model: `paginate(model=Book, ...)` is a `Page[Book]`, and mypy checks it against the signature of the endpoint.

The query parameters are named `current_page` and `items_by_page`, like the ones the library writes in the URLs of the previous and next pages, so a client can follow them as they are.

### The page

With six books by Jane Austen in the table, `GET /books?author=jane austen&current_page=2&items_by_page=2` returns:

```json
--8<-- "docs_src/books/response.json"
```

The filter narrows the count as well as the items: `item_count` is six, not the size of the table.

### The same page from a graph

With Neontology, the endpoint changes its import, not its response:

```python hl_lines="4  13-17"
--8<-- "docs_src/people/app.py"
```

`Person` is a Neontology node, defined on the [Neontology page](neontology.md), and the response has the same seven fields as the page of books.

### Interactive documentation

FastAPI documents `Page[Book]` as its own schema, named `Page_Book_`, whose `items` are `Book` objects, so the generated clients and the `/docs` page show the real item type.

## License

This project is licensed under the terms of the [MIT license](https://github.com/BiBzz/fastapi-object-pagination/blob/development/LICENSE).
