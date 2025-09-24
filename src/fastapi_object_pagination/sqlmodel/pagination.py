from math import ceil

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
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession


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
