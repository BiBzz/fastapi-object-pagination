# Changelog

Notable changes to this project, newest first.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-28

First version published on PyPI. 0.1.0 only ever existed in the internal
repository.

### Added

- `Page`, a generic Pydantic page carrying the items, `item_count`,
  `page_count`, `current_page`, `items_by_page`, and the previous and next page
  URLs.
- `paginate` for SQLModel, over an `AsyncSession`, with Django-style filters and
  ordering.
- `paginate` and `paginate_related` for Neontology, the second one over a list
  of relationship classes.
- An optional `serializer` on both Neontology entry points, so a page can carry
  an API model rather than the node that was queried. The page is then typed on
  what the serializer returns.
- The `sqlmodel` and `neontology` extras. Importing a backend whose extra is
  missing raises `ImportError` naming the command that installs it, rather than
  a bare `ModuleNotFoundError` from deep inside the call stack.
- Type information shipped with the package (`py.typed`), with overloads so the
  item type of a page is inferred at the call site.
- On PostgreSQL, the `in` lookup compiles to `= ANY(ARRAY[...])` instead of
  `IN (...)`, which plans better on long lists. Other dialects keep `IN`.

[Unreleased]: https://github.com/BiBzz/fastapi-object-pagination/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/BiBzz/fastapi-object-pagination/releases/tag/v0.1.1
