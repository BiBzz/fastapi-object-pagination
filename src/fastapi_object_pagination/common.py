from typing import Generic, TypeVar

from pydantic import BaseModel

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
