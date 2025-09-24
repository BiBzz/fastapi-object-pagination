from typing import Any

from sqlalchemy import inspect
from sqlalchemy.sql.expression import BinaryExpression
from sqlmodel import SQLModel, and_, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

Clause = BinaryExpression
Params = dict[str, Any]


def is_postgresql(session):
    """Check if the current session uses PostgreSQL."""
    dialect = inspect(session.bind).dialect.name
    return dialect == "postgresql"


def get_in_clause(session, column, values):
    """Return the appropriate IN/ANY clause based on the dialect."""
    from sqlalchemy.sql.expression import any_

    if not values:
        return column == False

    if is_postgresql(session):
        return column == any_(values)  # ANY(ARRAY[...]) optimized for PostgreSQL
    else:
        return column.in_(values)  # IN (...) for SQLite/MySQL


def _filters_to_where_clause(
    session: AsyncSession,
    filters: dict[tuple[type[SQLModel], str], Any] | None = None,
) -> tuple[Clause | None, Params]:
    """Convert a dictionary of filters into a WHERE clause and parameter dictionary for a query for SQLModel.

    Args:
        filters (dict | None): A dictionary of filters. Each key is a field name possibly followed
                            by '__' and a lookup type (e.g., 'exact', 'contains'). The value is
                            the filter value. If None, returns an empty WHERE clause.

    Returns:
        tuple: A tuple containing the WHERE clause string and a dictionary of parameters.
    """
    if not filters:
        return None, {}

    params = {}
    where_clauses = []

    for (model, field_lookup), value in filters.items():
        if "__" in field_lookup:
            field_name, lookup_type = field_lookup.split("__", 1)
        else:
            field_name, lookup_type = field_lookup, "exact"

        try:
            column = getattr(model, field_name)
        except AttributeError:
            raise ValueError(f"Attribute '{field_name}' not found in {model.__name__}")

        param_name = f"filter_{model.__tablename__}_{field_name}_{lookup_type}"
        params[param_name] = value

        if lookup_type == "exact":
            clause = (
                column
                == select([func.jsonb_build_object(param_name, value)]).as_scalar()
            )
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
            raise ValueError(f"Unkown lookup: {lookup_type}")

        where_clauses.append(clause)

    combined_clause = and_(*where_clauses) if where_clauses else None
    return combined_clause, params
