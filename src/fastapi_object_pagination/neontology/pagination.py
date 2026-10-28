from collections.abc import Callable
from math import ceil
from typing import Any, TypeVar, cast, overload

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
from neontology import BaseNode, BaseRelationship, GraphConnection  # noqa: E402

from fastapi_object_pagination.neontology.clauses import (  # noqa: E402
    Filters,
    _postfixes,
    _prefixes,
)

N = TypeVar("N", bound=BaseNode)


@overload
async def paginate(
    model: type[N],
    current_page: int = ...,
    items_by_page: int = ...,
    filters: Filters | None = ...,
    serializer: None = ...,
) -> Page[N]: ...


@overload
async def paginate(
    model: type[N],
    current_page: int = ...,
    items_by_page: int = ...,
    filters: Filters | None = ...,
    *,
    serializer: Callable[[N], M],
) -> Page[M]: ...


async def paginate(
    model: type[N],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: Filters | None = None,
    serializer: Callable[[N], M] | None = None,
) -> Page[N] | Page[M]:
    """
    Paginate a list of items from a Cypher model.
    Returns a Page object containing the paginated items, total count, current page,
    items per page, and total pages.

    :param model: The Cypher model to paginate.
    :param current_page: The current page number.
    :param items_by_page: The number of items per page.
    :param filters: A dictionary of filters to apply to the query.
    :param serializer: Maps each node to the model the page should carry.
    :return: A Page object containing the paginated items and pagination metadata.
    """
    node_model: type[BaseNode] = model
    item_count = node_model.get_count(filters=filters)

    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0

    offset = (current_page - 1) * items_by_page

    items: list[Any] = node_model.match_nodes(
        skip=offset, limit=items_by_page, filters=filters
    )

    if serializer is not None:
        items = [serializer(item) for item in items]

    opts: dict[str, Any] = {
        "current_page": current_page,
        "items_by_page": items_by_page,
    }

    return cast(
        "Page[N] | Page[M]",
        Page[M](
            items=items,
            item_count=item_count,
            page_count=page_count,
            current_page=current_page,
            items_by_page=items_by_page,
            previous_page_url=await _get_previous_page_url(opts),
            next_page_url=await _get_next_page_url(opts, page_count),
        ),
    )


@overload
async def paginate_related(
    model: type[N],
    relationships: list[type[BaseRelationship]],
    current_page: int = ...,
    items_by_page: int = ...,
    filters: Filters | None = ...,
    ordering: list[str] | None = ...,
    serializer: None = ...,
) -> Page[N]: ...


@overload
async def paginate_related(
    model: type[N],
    relationships: list[type[BaseRelationship]],
    current_page: int = ...,
    items_by_page: int = ...,
    filters: Filters | None = ...,
    ordering: list[str] | None = ...,
    *,
    serializer: Callable[[N], M],
) -> Page[M]: ...


async def paginate_related(
    model: type[N],
    relationships: list[type[BaseRelationship]],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: Filters | None = None,
    ordering: list[str] | None = None,
    serializer: Callable[[N], M] | None = None,
) -> Page[N] | Page[M]:
    """
    Paginate the nodes of `model` that are connected through `relationships`.

    :param model: The Cypher model to paginate.
    :param relationships: The relationship classes the nodes must take part in.
    :param current_page: The current page number.
    :param items_by_page: The number of items per page.
    :param filters: A dictionary of filters to apply to the query.
    :param ordering: A list of fields to order the query by.
    :param serializer: Maps each node to the model the page should carry.
    :return: A Page object containing the paginated items and pagination metadata.
    """
    node_model: type[BaseNode] = model
    alias = node_model.__primarylabel__.lower()
    cypher, params = await _prefixes(node_model, relationships, filters)
    count_cypher = cypher + f" RETURN COUNT(DISTINCT {alias})"

    gc = GraphConnection()

    offset = (current_page - 1) * items_by_page
    cypher += f" RETURN DISTINCT {alias}"
    postfixes_cypher, postfixes_params = await _postfixes(
        node_model, params, ordering, offset, items_by_page
    )
    cypher += postfixes_cypher
    params.update(postfixes_params)

    items: list[Any] = gc.evaluate_query(
        cypher, params, node_classes={node_model.__primarylabel__: node_model}
    ).nodes
    item_count = gc.evaluate_query_single(count_cypher, params)
    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0

    if serializer is not None:
        items = [serializer(item) for item in items]

    opts: dict[str, Any] = {
        "current_page": current_page,
        "items_by_page": items_by_page,
    }

    return cast(
        "Page[N] | Page[M]",
        Page[M](
            items=items,
            item_count=item_count,
            page_count=page_count,
            current_page=current_page,
            items_by_page=items_by_page,
            previous_page_url=await _get_previous_page_url(opts),
            next_page_url=await _get_next_page_url(opts, page_count),
        ),
    )
