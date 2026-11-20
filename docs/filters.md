---
description: "The filter lookups of fastapi-object-pagination, exact to isnull, and the SQL and Cypher each one becomes on SQLModel and Neontology."
---

# Filters

A filter is a dictionary entry: the key names a field and, after a double underscore, a lookup; the value is what the field is compared with. A key without a lookup means `exact`. Several entries are joined with `AND`, and they narrow the count as well as the items.

| Backend | Key | Example |
| --- | --- | --- |
| SQLModel | `"field__lookup"` | `{"author__iexact": "jane austen"}` |
| Neontology | `(NodeClass, "field__lookup")` | `{(Company, "name__iexact"): "acme"}` |

Neontology keys carry the node class because a query from `paginate_related` matches several labels and can filter on any of them.

## Lookups

The SQL column is `book.title` (or `book.year`), filtered with `"title__<lookup>"`; the Cypher property is `person.name` (or `person.year`), filtered with `(Person, "name__<lookup>")`. The SQL is shown with its values written in; the query sends them as parameters.

| Lookup | SQL, SQLModel | Cypher, Neontology |
| --- | --- | --- |
| `exact` | `book.title = 'Emma'` | `person.name = $filter_person_name_exact` |
| `iexact` | `lower(book.title) = lower('Emma')` | `toLower(person.name) = toLower($filter_person_name_iexact)` |
| `contains` | `book.title LIKE '%mm%'` | `person.name CONTAINS $filter_person_name_contains` |
| `icontains` | `lower(book.title) LIKE '%mm%'` | `toLower(person.name) CONTAINS toLower($filter_person_name_icontains)` |
| `startswith` | `book.title LIKE 'Em%'` | `person.name STARTS WITH $filter_person_name_startswith` |
| `istartswith` | `lower(book.title) LIKE 'em%'` | `toLower(person.name) STARTS WITH toLower($filter_person_name_istartswith)` |
| `endswith` | `book.title LIKE '%ma'` | `person.name ENDS WITH $filter_person_name_endswith` |
| `iendswith` | `lower(book.title) LIKE '%ma'` | `toLower(person.name) ENDS WITH toLower($filter_person_name_iendswith)` |
| `gt` | `book.year > 1814` | `person.year > $filter_person_year_gt` |
| `gte` | `book.year >= 1814` | `person.year >= $filter_person_year_gte` |
| `lt` | `book.year < 1814` | `person.year < $filter_person_year_lt` |
| `lte` | `book.year <= 1814` | `person.year <= $filter_person_year_lte` |
| `in` | `book.title IN ('Emma', 'Persuasion')` | `person.name IN $filter_person_name_in` |
| `isnull`, `True` | `book.title IS NULL` | `person.name IS NULL` |
| `isnull`, `False` | `book.title IS NOT NULL` | `person.name IS NOT NULL` |

The Cypher column is what `paginate_related` writes. For `paginate`, read the warning on the [Neontology page](neontology.md#filtering-a-single-label).

## SQLModel details

- `icontains`, `istartswith` and `iendswith` lower the value in Python, so it must be a string.
- `contains`, `startswith` and `endswith` use `LIKE`, whose case sensitivity depends on the database (SQLite compares ASCII letters without case, PostgreSQL with case). A `%` or a `_` in the value keeps its `LIKE` meaning.
- `in` takes a list, a tuple or a set, and raises `ValueError` for anything else. An empty one matches no row (`0 = 1`).
- On PostgreSQL, `in` becomes `book.title = ANY(%(param_1)s)`, with the whole list bound as one array parameter.
- A field the model does not have, or a lookup not in the table, raises `ValueError` before any query is sent.

## Neontology details

- Values are always query parameters, named `filter_<label>_<field>_<lookup>` in lower case.
- Labels and property names are written into the query text: build the keys in your code, never from what a client sends.
- A lookup not in the table is compared with `=`, without error.
