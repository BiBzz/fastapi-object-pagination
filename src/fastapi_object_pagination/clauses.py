from typing import Any
from neontology import BaseNode, BaseRelationship

Clause = str
Params = dict


def _cypher_relation_to_match_clause(relation_class: BaseRelationship) -> Clause:
    """
    Convert a relationship to a MATCH clause for a query.
    Args:
        relation_class (BaseRelationship): The relationship class to convert.
    Returns:
        str: The MATCH clause for the relationship.
    """
    if not issubclass(relation_class, BaseRelationship):
        raise ValueError("relation_class must be a subclass of BaseRelationship")
    params = {}
    source = relation_class.model_fields["source"].annotation.__primarylabel__
    target = relation_class.model_fields["target"].annotation.__primarylabel__
    return f" MATCH ({source.lower()}:{source})-[:{relation_class.__relationshiptype__}]-({target.lower()}:{target})"


def _filters_to_where_clause(
    filters: dict[tuple, str] | None = None,
) -> tuple[Clause, Params]:
    """Convert a dictionary of filters into a WHERE clause and parameter dictionary for a query.

    Args:
        filters (dict | None): A dictionary of filters. Each key is a field name possibly followed
                            by '__' and a lookup type (e.g., 'exact', 'contains'). The value is
                            the filter value. If None, returns an empty WHERE clause.

    Returns:
        tuple: A tuple containing the WHERE clause string and a dictionary of parameters.
    """
    params = {}
    where_clauses = []
    if filters:
        for key, value in filters.items():
            if not isinstance(key, tuple) and not issubclass(key[0], BaseNode):
                raise ValueError("Filter keys must be tuples of (model, field)")
            alias = key[0].__primarylabel__.lower()
            if "__" in key[1]:
                field_name, lookup_type = key[1].split("__")
            else:
                field_name, lookup_type = key[1], "exact"
            param_name = f"filter_{alias}_{field_name}_{lookup_type}"
            params[param_name] = value
            if lookup_type == "exact":
                clause = f"{alias}.{field_name} = ${param_name}"
            elif lookup_type == "iexact":
                clause = f"toLower({alias}.{field_name}) = toLower(${param_name})"
            elif lookup_type == "startswith":
                clause = f"{alias}.{field_name} STARTS WITH ${param_name}"
            elif lookup_type == "istartswith":
                clause = (
                    f"toLower({alias}.{field_name}) STARTS WITH toLower(${param_name})"
                )
            elif lookup_type == "contains":
                clause = f"{alias}.{field_name} CONTAINS ${param_name}"
            elif lookup_type == "icontains":
                clause = (
                    f"toLower({alias}.{field_name}) CONTAINS toLower(${param_name})"
                )
            elif lookup_type == "endswith":
                clause = f"{alias}.{field_name} ENDS WITH ${param_name}"
            elif lookup_type == "iendswith":
                clause = (
                    f"toLower({alias}.{field_name}) ENDS WITH toLower(${param_name})"
                )
            elif lookup_type in ("gt", "lt", "gte", "lte"):
                operator = {"gt": ">", "lt": "<", "gte": ">=", "lte": "<="}[lookup_type]
                clause = f"{alias}.{field_name} {operator} ${param_name}"
            elif lookup_type == "in":
                clause = f"{alias}.{field_name} IN ${param_name}"
            elif lookup_type == "isnull":
                clause = (
                    f"{alias}.{field_name} IS NULL"
                    if value
                    else f"{alias}.{field_name} IS NOT NULL"
                )
            else:
                clause = f"{alias}.{field_name} = ${param_name}"
            where_clauses.append(clause)
    where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    return where_clause, params


def _ordering_to_order_by_clause(model: BaseNode, ordering: list[str]) -> Clause:
    """
    Convert ordering to ORDER BY clause.
    This function is used to convert ordering to ORDER BY clause.
    It returns a string containing the ORDER BY clause.
    :param ordering: The ordering to convert.
    :return: A string containing the ORDER BY clause.
    """
    alias = model.__primarylabel__.lower()
    order_by_clauses = []
    for field in ordering:
        if field.startswith("-"):
            order_by_clauses.append(f"{alias}.{field[1:]} DESC")
        else:
            order_by_clauses.append(f"{alias}.{field} ASC")
    order_by_clause = (
        " ORDER BY " + ", ".join(order_by_clauses) if order_by_clauses else ""
    )
    return order_by_clause


def _prefixes(
    model: BaseNode,
    relationships: list[str] | None = None,
    filters: dict[str, Any] | None = None,
) -> tuple[Clause, Params]:
    params = {}
    alias = model.__primarylabel__.lower()
    cypher = f"MATCH ({alias}:{model.__primarylabel__})"
    if relationships:
        for relationship in relationships:
            cypher += _cypher_relation_to_match_clause(relationship)
    if filters:
        where_clause, where_params = _filters_to_where_clause(filters)
        cypher += where_clause
        params.update(where_params)
    return cypher, params


def _postfixes(
    model: BaseNode,
    params: Params,
    ordering: list[str] | None = None,
    offset: int | None = None,
    items_by_page: int | None = None,
) -> tuple[Clause, Params]:
    cypher = ""
    if ordering:
        cypher += _ordering_to_order_by_clause(model, ordering)
    if offset is not None:
        cypher += " SKIP $skip"
        params["skip"] = offset
    if items_by_page is not None:
        cypher += " LIMIT $limit"
        params["limit"] = items_by_page
    return cypher, params
