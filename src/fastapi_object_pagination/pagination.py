from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlmodel import SQLModel, select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from neontology import BaseNode, GraphConnection
from .clauses import _prefixes, _postfixes

M = TypeVar("M", bound=BaseModel)


class Page(BaseModel, Generic[M]):
    items: list[M]
    item_count: int
    page_count: int
    current_page: int
    items_by_page: int
    previous_page_url: str | None
    next_page_url: str | None


def _get_page_url(opts: dict = {}) -> str:
    opts_str = "&".join(f"{k}={v}" for k, v in opts.items())
    return f"?{opts_str}"


def _get_previous_page_url(opts: dict = {}) -> str | None:
    if opts["current_page"] <= 1:
        return None
    local_opts = opts.copy()
    local_opts["current_page"] -= 1
    return _get_page_url(local_opts)


def _get_next_page_url(opts: dict = {}, page_count: int | None = None) -> str | None:
    if page_count is None or opts["current_page"] >= page_count:
        return None
    local_opts = opts.copy()
    local_opts["current_page"] += 1
    return _get_page_url(local_opts)


async def paginate(
    model: SQLModel,
    async_session: AsyncSession,
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict | None = None,
    ordering: list[str] | None = None,
) -> Page[M]:
    """
    Paginate a list of items from SQLModel.
    This function is used to paginate a list of items from a SQLModel model.
    It returns a Page object containing the paginated items and pagination metadata.

    :param model: The SQLModel model to paginate.
    :param async_session: The async SQL session.
    :param current_page: The current page number.
    :param items_by_page: The number of items to display per page.
    :param filters: A dictionary of filters to apply to the query.
    :param ordering: A list of fields to order the query by.
    :return: A Page object containing the paginated items and pagination metadata.
    """
    statement = select(model)
    if filters:
        for key, value in filters.items():
            statement = statement.where(getattr(model, key) == value)
    if ordering:
        for order in ordering:
            key = order.lstrip("-")
            if order[0] == "-":
                ordering_key = getattr(model, key).desc()
            else:
                ordering_key = getattr(model, key).asc()
            statement = statement.order_by(ordering_key)
    paginated_statement = statement.offset((current_page - 1) * items_by_page).limit(
        items_by_page
    )
    async with async_session as async_session:
        items = await async_session.exec(paginated_statement)
        item_count = (
            await async_session.exec(
                select(func.count()).select_from(statement.subquery())
            )
        ).one()
    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0

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
        previous_page_url=_get_previous_page_url(opts),
        next_page_url=_get_next_page_url(opts, page_count),
    )


async def cypher_paginate(
    model: BaseNode,
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict | None = None,
) -> Page[M]:
    """
    Paginate a list of items from a Cypher model.
    Returns a dictionary containing the paginated items, total count, current current_page, items per current_page, and total pages.
    It assumes that the `model` has a `match_nodes` method that accepts `skip` and `limit` parameters.

    :param model: The Cypher model to paginate.
    :param current_page: The current page number.
    :param items_by_page: The number of items per page.
    :param filters: A dictionary of filters to apply to the query.
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
        previous_page_url=_get_previous_page_url(opts),
        next_page_url=_get_next_page_url(opts, page_count),
    )


async def cypher_paginate_related(
    model: BaseNode,
    relationships: list[str],
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict | None = None,
    ordering: list[str] | None = None,
) -> Page[M]:
    alias = model.__primarylabel__.lower()
    cypher, params = _prefixes(model, relationships, filters)
    count_cypher = cypher + f" RETURN COUNT(DISTINCT {alias})"

    gc = GraphConnection()

    offset = (current_page - 1) * items_by_page
    cypher += f" RETURN DISTINCT {alias}"
    _postfixes_cypher, _postfixes_params = _postfixes(
        model, params, ordering, offset, items_by_page
    )
    cypher += _postfixes_cypher
    params.update(_postfixes_params)

    items = gc.evaluate_query(
        cypher, params, node_classes={model.__primarylabel__: model}
    ).nodes
    item_count = gc.evaluate_query_single(count_cypher, params)
    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0

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
        previous_page_url=_get_previous_page_url(opts),
        next_page_url=_get_next_page_url(opts, page_count),
    )
