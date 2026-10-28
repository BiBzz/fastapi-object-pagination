from typing import Any

from neontology import BaseNode, BaseRelationship

Clause = str
Params = dict[str, Any]
Filters = dict[tuple[type[BaseNode], str], Any]


async def _cypher_relation_to_match_clause(
    relation_class: type[BaseRelationship],
) -> Clause:
    """
    Convert a relationship to a MATCH clause for a query.
    Args:
        relation_class (BaseRelationship): The relationship class to convert.
    Returns:
        str: The MATCH clause for the relationship.
    """
    if not issubclass(relation_class, BaseRelationship):
        raise ValueError("relation_class must be a subclass of BaseRelationship")
    source = relation_class.model_fields["source"].annotation.__primarylabel__
    target = relation_class.model_fields["target"].annotation.__primarylabel__
    return (
        f" MATCH ({source.lower()}:{source})"
        f"-[:{relation_class.__relationshiptype__}]-"
        f"({target.lower()}:{target})"
    )


async def _filters_to_where_clause(
    filters: Filters | None = None,
) -> tuple[Clause, Params]:
    """Convert filters into a WHERE clause and its parameter dictionary.

    Args:
        filters (dict | None): A dictionary of filters. Each key is a field name,
            optionally followed by '__' and a lookup type (for example 'exact' or
            'contains'). The value is the filter value. If None, no WHERE clause
            is produced.

    Returns:
        tuple: The WHERE clause string and its dictionary of parameters.
    """
    params: Params = {}
    where_clauses = []
    if filters:
        for key, value in filters.items():
            if not isinstance(key, tuple) or not issubclass(key[0], BaseNode):
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


async def _ordering_to_order_by_clause(
    model: type[BaseNode], ordering: list[str]
) -> Clause:
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
    return " ORDER BY " + ", ".join(order_by_clauses) if order_by_clauses else ""


async def _prefixes(
    model: type[BaseNode],
    relationships: list[type[BaseRelationship]] | None = None,
    filters: Filters | None = None,
) -> tuple[Clause, Params]:
    params: Params = {}
    alias = model.__primarylabel__.lower()
    cypher = f"MATCH ({alias}:{model.__primarylabel__})"
    if relationships:
        for relationship in relationships:
            cypher += await _cypher_relation_to_match_clause(relationship)
    if filters:
        where_clause, where_params = await _filters_to_where_clause(filters)
        cypher += where_clause
        params.update(where_params)
    return cypher, params


async def _postfixes(
    model: type[BaseNode],
    params: Params,
    ordering: list[str] | None = None,
    offset: int | None = None,
    items_by_page: int | None = None,
) -> tuple[Clause, Params]:
    cypher = ""
    if ordering:
        cypher += await _ordering_to_order_by_clause(model, ordering)
    if offset is not None:
        cypher += " SKIP $skip"
        params["skip"] = offset
    if items_by_page is not None:
        cypher += " LIMIT $limit"
        params["limit"] = items_by_page
    return cypher, params
