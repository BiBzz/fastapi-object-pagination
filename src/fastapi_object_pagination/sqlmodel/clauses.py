from typing import Any

from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.expression import any_, false
from sqlmodel import and_, func
from sqlmodel.ext.asyncio.session import AsyncSession

Clause = ColumnElement[bool]


def is_postgresql(session: AsyncSession) -> bool:
    """Check if the current session uses PostgreSQL."""
    try:
        return session.get_bind().dialect.name == "postgresql"
    except Exception:
        return False


def get_in_clause(session: AsyncSession, column: Any, values: Any) -> Any:
    """Return the appropriate IN/ANY clause based on the dialect."""
    if not values:
        return false()

    if is_postgresql(session):
        return column == any_(values)  # ANY(ARRAY[...]) optimized for PostgreSQL
    return column.in_(values)


async def _filters_to_where_clause(
    session: AsyncSession,
    model: type[Any],
    filters: dict[str, Any] | None = None,
) -> Clause | None:
    """Convert a dictionary of filters into a WHERE clause for a SQLModel query.

    Args:
        filters (dict | None): A dictionary of filters. Each key is a field name,
            optionally followed by '__' and a lookup type (for example 'exact' or
            'contains'). The value is the filter value. If None, no WHERE clause
            is produced.

    Returns:
        clauses: A tuple containing the WHERE clause string
    """
    if not filters:
        return None

    where_clauses = []

    for field_lookup, value in filters.items():
        if "__" in field_lookup:
            field_name, lookup_type = field_lookup.split("__", 1)
        else:
            field_name, lookup_type = field_lookup, "exact"

        try:
            column = getattr(model, field_name)
        except AttributeError as error:
            raise ValueError(
                f"Attribute '{field_name}' not found in {model.__name__}"
            ) from error

        if lookup_type == "exact":
            clause = column == value

        elif lookup_type == "iexact":
            clause = func.lower(column) == func.lower(value)

        elif lookup_type == "contains":
            clause = column.like(f"%{value}%")

        elif lookup_type == "icontains":
            clause = func.lower(column).like(f"%{value.lower()}%")

        elif lookup_type == "startswith":
            clause = column.like(f"{value}%")

        elif lookup_type == "istartswith":
            clause = func.lower(column).like(f"{value.lower()}%")

        elif lookup_type == "endswith":
            clause = column.like(f"%{value}")

        elif lookup_type == "iendswith":
            clause = func.lower(column).like(f"%{value.lower()}")

        elif lookup_type in ("gt", "lt", "gte", "lte"):
            operator = {
                "gt": column.__gt__,
                "lt": column.__lt__,
                "gte": column.__ge__,
                "lte": column.__le__,
            }[lookup_type]
            clause = operator(value)

        elif lookup_type == "in":
            if not isinstance(value, (list, tuple, set)):
                raise ValueError(
                    f"Value for `in` should be an iterable and not {type(value)}"
                )
            clause = get_in_clause(session, column, value)

        elif lookup_type == "isnull":
            clause = column.is_(None) if value else column.isnot(None)

        else:
            raise ValueError(f"Unknown lookup: {lookup_type}")

        where_clauses.append(clause)

    return and_(*where_clauses) if where_clauses else None
