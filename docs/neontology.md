---
description: "Paginate Neontology nodes from Neo4j or Memgraph in a FastAPI endpoint with fastapi-object-pagination: paginate, paginate_related, filters across labels and serializers."
---

# Neontology

The Neontology backend pages the nodes of a label stored in Neo4j or Memgraph, and returns the same `Page` as the SQLModel backend.

## Install and connect

```console
$ pip install 'fastapi-object-pagination[neontology]'
```

The library runs its queries on the connection Neontology already holds: initialise Neontology once when the application starts, as its <a href="https://neontology.readthedocs.io/" target="_blank">documentation</a> explains. Nothing is passed to the pagination functions.

## The models

The examples on this page use two labels and one relationship:

```python
--8<-- "docs_src/people/models.py"
```

## A page of nodes

```python hl_lines="4  13-17"
--8<-- "docs_src/people/app.py"
```

`paginate` asks Neontology for the number of `Person` nodes, then for the requested page, with `SKIP` and `LIMIT`. With three people in the graph, `GET /people?items_by_page=2` returns:

```json
--8<-- "docs_src/people/response.json"
```

## An API model in the page

When the page should carry something else than the node, pass a `serializer`: a function from the node to a Pydantic model. Each node of the page goes through it, and the page is typed on what it returns, here `Page[PersonOut]`:

```python hl_lines="12  13  16  17  23  28"
--8<-- "docs_src/people/serializer.py"
```

The counts and the URLs are those of the nodes: only the items change. `serializer` is a keyword argument, on `paginate` and on `paginate_related`.

## Nodes connected to another label

`paginate_related` pages the nodes of a label that take part in a list of relationships, and accepts filters on every label those relationships reach. The employees of a company:

```python hl_lines="4  15-22"
--8<-- "docs_src/people/related.py"
```

For `GET /companies/Acme/employees?current_page=3` it sends two queries, one for the page and one for the count:

```cypher
--8<-- "docs_src/people/related.cypher"
```

- Each relationship class becomes a `MATCH` between its `source` and `target` labels, in either direction.
- Every node is bound to its label in lower case (`person`, `company`), so a filter on `(Company, "name__iexact")` reads `company.name`, and the clauses join on the labels they share.
- `RETURN DISTINCT` and `COUNT(DISTINCT ...)` return and count each person once, however many relationships match them.
- Values are sent as query parameters (`$filter_company_name_iexact`, `$skip`, `$limit`).
- `ordering` sorts on properties of the paginated node.

## Filtering a single label

!!! warning "Filters on `paginate`, in version 0.1.1"
    `paginate` hands its `filters` to Neontology's own `match_nodes` and `get_count`, which expect plain keys (`{"city__iexact": "Paris"}`), while its signature declares `(node class, field)` keys like `paginate_related`. With the declared keys, the query Neontology builds is invalid. Until this is fixed, filter a single label with `paginate_related` and an empty list of relationships, as below.

```python hl_lines="15-22"
--8<-- "docs_src/people/filtered.py"
```

With no relationship, the query matches the label alone:

```cypher
--8<-- "docs_src/people/filtered.cypher"
```

## The calls

```python
await paginate(
    model=Person,
    current_page=1,
    items_by_page=10,
    filters=None,
    serializer=None,
)

await paginate_related(
    model=Person,
    relationships=[WorksFor],
    current_page=1,
    items_by_page=10,
    filters=None,
    ordering=None,
    serializer=None,
)
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `model` | | the Neontology node class to page, and the type of the items without a serializer |
| `relationships` | | `paginate_related` only: the relationship classes the nodes must take part in, possibly empty |
| `current_page` | `1` | the page to return, starting at 1 |
| `items_by_page` | `10` | the size of a page |
| `filters` | `None` | a dictionary of `(NodeClass, "field__lookup"): value` filters, see [filters](filters.md) |
| `ordering` | `None` | `paginate_related` only: property names of `model`, each descending when it starts with `-` |
| `serializer` | `None` | a function from a node to the Pydantic model the page carries |

## Good to know

- **The queries are synchronous.** `paginate` and `paginate_related` are coroutines, like the SQLModel `paginate`, but Neontology talks to the database through the synchronous Neo4j driver: the event loop waits while the graph answers.
- **Property names are written into the Cypher text.** Values are parameters, but the field names of the filters and of the ordering are not: build them in your code, never from what a client sends.
- **One variable per label.** A relationship between two nodes of the same label, such as `(:Person)-[:KNOWS]-(:Person)`, binds both ends to `person`, and only matches a node related to itself.
- **An unknown lookup is an equality.** Where the SQLModel backend raises `ValueError`, `paginate_related` compares with `=` when the lookup after `__` is not one it knows.
