import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi_object_pagination import Page
from fastapi_object_pagination.sqlmodel import paginate
from tests.conftest import Hero

pytestmark = pytest.mark.sqlmodel


async def test_first_page_has_no_previous_url(session: AsyncSession) -> None:
    page = await paginate(model=Hero, async_session=session, items_by_page=10)

    assert isinstance(page, Page)
    assert len(page.items) == 10
    assert page.item_count == 25
    assert page.page_count == 3
    assert page.current_page == 1
    assert page.previous_page_url is None
    assert page.next_page_url == "?current_page=2&items_by_page=10"


async def test_middle_page_links_both_ways(session: AsyncSession) -> None:
    page = await paginate(
        model=Hero, async_session=session, current_page=2, items_by_page=10
    )

    assert [hero.name for hero in page.items] == [
        f"hero-{i:02d}" for i in range(10, 20)
    ]
    assert page.previous_page_url == "?current_page=1&items_by_page=10"
    assert page.next_page_url == "?current_page=3&items_by_page=10"


async def test_last_page_is_partial_and_has_no_next_url(session: AsyncSession) -> None:
    page = await paginate(
        model=Hero, async_session=session, current_page=3, items_by_page=10
    )

    assert len(page.items) == 5
    assert page.next_page_url is None


async def test_filters_narrow_the_count_not_only_the_items(
    session: AsyncSession,
) -> None:
    page = await paginate(
        model=Hero,
        async_session=session,
        items_by_page=5,
        filters={"team": "preventers"},
    )

    assert page.item_count == 12
    assert page.page_count == 3
    assert all(hero.team == "preventers" for hero in page.items)


async def test_lookups_are_applied(session: AsyncSession) -> None:
    page = await paginate(
        model=Hero,
        async_session=session,
        items_by_page=100,
        filters={"name__startswith": "hero-2"},
    )

    assert page.item_count == 5
    assert {hero.name for hero in page.items} == {f"hero-2{i}" for i in range(5)}


async def test_in_lookup_accepts_a_list(session: AsyncSession) -> None:
    page = await paginate(
        model=Hero,
        async_session=session,
        items_by_page=100,
        filters={"name__in": ["hero-00", "hero-07"]},
    )

    assert page.item_count == 2


async def test_descending_ordering(session: AsyncSession) -> None:
    page = await paginate(
        model=Hero, async_session=session, items_by_page=3, ordering=["-name"]
    )

    assert [hero.name for hero in page.items] == ["hero-24", "hero-23", "hero-22"]


async def test_unknown_field_raises_value_error(session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="nickname"):
        await paginate(
            model=Hero, async_session=session, filters={"nickname": "anything"}
        )


async def test_unknown_lookup_raises_value_error(session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="Unknown lookup"):
        await paginate(
            model=Hero, async_session=session, filters={"name__sounds_like": "hero"}
        )


async def test_session_stays_usable_after_pagination(session: AsyncSession) -> None:
    await paginate(model=Hero, async_session=session, items_by_page=2)
    second = await paginate(model=Hero, async_session=session, items_by_page=2)

    assert second.item_count == 25
