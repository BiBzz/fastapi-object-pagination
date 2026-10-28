from math import ceil
from typing import Any, cast

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

check_optional_deps(ORM.SQLMODEL)
from sqlmodel import func, select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from fastapi_object_pagination.sqlmodel.clauses import (  # noqa: E402
    _filters_to_where_clause,
)


async def paginate(
    model: type[M],
    async_session: AsyncSession,
    current_page: int = 1,
    items_by_page: int = 10,
    filters: dict[str, Any] | None = None,
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
    where_clause = await _filters_to_where_clause(
        session=async_session,
        model=model,
        filters=filters,
    )
    if where_clause is not None:
        statement = statement.where(where_clause)
    if ordering:
        for order in ordering:
            key = order.lstrip("-")
            if order.startswith("-"):
                ordering_key = getattr(model, key).desc()
            else:
                ordering_key = getattr(model, key).asc()
            statement = statement.order_by(ordering_key)
    paginated_statement = statement.offset((current_page - 1) * items_by_page).limit(
        items_by_page
    )
    items = cast("list[M]", list((await async_session.exec(paginated_statement)).all()))
    item_count = (
        await async_session.exec(select(func.count()).select_from(statement.subquery()))
    ).one()
    page_count = ceil(item_count / items_by_page) if items_by_page > 0 else 0

    opts: dict[str, Any] = {
        "current_page": current_page,
        "items_by_page": items_by_page,
    }

    return Page[M](
        items=items,
        item_count=item_count,
        page_count=page_count,
        current_page=current_page,
        items_by_page=items_by_page,
        previous_page_url=await _get_previous_page_url(opts),
        next_page_url=await _get_next_page_url(opts, page_count),
    )
