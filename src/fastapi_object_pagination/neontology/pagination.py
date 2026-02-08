from math import ceil
from typing import Callable, Any
from fastapi_object_pagination.check_optional_dependencies import (
    ORM,
    check_optional_deps,
)
from fastapi_object_pagination.common import (
    M,
    Page,
    _get_next_page_url,
    _get_previous_page_url,
)

check_optional_deps(ORM.NEONTOLOGY)
from neontology import BaseNode, GraphConnection

from .clauses import _postfixes, _prefixes


async def paginate(
    model: type[BaseNode],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict | None = None,
    serializer: Callable[[Any], M] | None = None,
) -> Page[M]:
    """
    Paginate a list of items from a Cypher model.
    Returns a dictionary containing the paginated items, total count, current current_page, items per current_page, and total pages.
    It assumes that the `model` has a `match_nodes` method that accepts `skip` and `limit` parameters.

    :param model: The Cypher model to paginate.
    :param current_page: The current page number.
    :param items_by_page: The number of items per page.
    :param filters: A dictionary of filters to apply to the query.
    :param serializer: An optional callable to serialize the items before returning them.
    :return: A dictionary containing the paginated items, total count, current current_page, items per current_page, and total pages.
    :raises ValueError: If `current_page` or `items_by_page` is less than 1.
    :raises TypeError: If `model` is not a subclass of `BaseNode`.
    :raises AttributeError: If `model` does not have a `match_nodes` method.
    :raises Exception: If any other error occurs during pagination.
    """
    item_count = model.get_count(filters=filters)
    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0
    offset = (current_page - 1) * items_by_page

    items = model.match_nodes(skip=offset, limit=items_by_page, filters=filters)

    if serializer is not None:
        items = [serializer(item) for item in items]

    opts = {"current_page": current_page, "items_by_page": items_by_page}

    return Page(
        items=items,
        item_count=item_count,
        page_count=page_count,
        current_page=current_page,
        items_by_page=items_by_page,
        previous_page_url=await _get_previous_page_url(opts),
        next_page_url=await _get_next_page_url(opts, page_count),
    )


async def paginate_related(
    model: BaseNode,
    relationships: list[str],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict | None = None,
    ordering: list[str] | None = None,
    serializer: Callable[[Any], M] | None = None,
) -> Page[M]:
    """
    Paginate a list of items from a Cypher model based on its relationships.
    Check paginate in the documentation for more details.
    :param model: The Cypher model to paginate.
    :param relationships: A list of relationship types to traverse in the query.
    :param current_page: The current page number.
    :param items_by_page: The number of items per page.
    :param filters: A dictionary of filters to apply to the query.
    :param ordering: A list of fields to order the results by.
    :param serializer: An optional callable to serialize the items before returning them.
    :return: A dictionary containing the paginated items, total count, current current_page, items per current_page, and total pages.
    :raises ValueError: If `current_page` or `items_by_page` is less than 1.
    :raises TypeError: If `model` is not a subclass of `BaseNode`.
    :raises AttributeError: If `model` does not have a `match_nodes` method.
    :raises Exception: If any other error occurs during pagination.
    """
    alias = model.__primarylabel__.lower()
    cypher, params = await _prefixes(model, relationships, filters)
    count_cypher = cypher + f" RETURN COUNT(DISTINCT {alias})"

    gc = GraphConnection()

    offset = (current_page - 1) * items_by_page
    cypher += f" RETURN DISTINCT {alias}"
    _postfixes_cypher, _postfixes_params = await _postfixes(
        model, params, ordering, offset, items_by_page
    )
    cypher += _postfixes_cypher
    params.update(_postfixes_params)
    items = gc.evaluate_query(
        cypher, params, node_classes={model.__primarylabel__: model}
    ).nodes
    item_count = gc.evaluate_query_single(count_cypher, params)
    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0

    if serializer is not None:
        items = [serializer(item) for item in items]

    opts = {
        "current_page": current_page,
        "items_by_page": items_by_page,
    }

    return Page(
        items=items,
        item_count=item_count,
        page_count=page_count,
        current_page=current_page,
        items_by_page=items_by_page,
        previous_page_url=await _get_previous_page_url(opts),
        next_page_url=await _get_next_page_url(opts, page_count),
    )