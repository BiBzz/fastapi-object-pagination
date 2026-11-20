import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx2 import ASGITransport, AsyncClient

from docs_src.people import app as people_app
from docs_src.people import filtered, related, serializer
from docs_src.people.models import Person, WorksFor
from fastapi_object_pagination.neontology import paginate, paginate_related, pagination

pytestmark = pytest.mark.neontology

EXAMPLES = Path(people_app.__file__).parent


def cypher_queries(name: str) -> list[str]:
    text = (EXAMPLES / name).read_text()
    return [" ".join(query.split()) for query in text.split("\n\n")]


PEOPLE = [
    Person(name="Ada", city="London"),
    Person(name="Alan", city="London"),
    Person(name="Grace", city="New York"),
]


def client_for(app: Any) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest.fixture
def matched(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def get_count(cls: type[Person], filters: Any = None) -> int:
        return len(PEOPLE)

    def match_nodes(
        cls: type[Person], limit: Any = None, skip: Any = None, filters: Any = None
    ) -> list[Person]:
        calls.append({"skip": skip, "limit": limit, "filters": filters})
        return PEOPLE[skip : skip + limit]

    monkeypatch.setattr(Person, "get_count", classmethod(get_count))
    monkeypatch.setattr(Person, "match_nodes", classmethod(match_nodes))
    return calls


class RecordingGraph:
    queries: list[tuple[str, dict[str, Any]]] = []

    def evaluate_query(self, cypher: str, params: Any, node_classes: Any) -> Any:
        self.queries.append((cypher, dict(params)))

        class Result:
            nodes = PEOPLE[:2]

        return Result()

    def evaluate_query_single(self, cypher: str, params: Any) -> int:
        self.queries.append((cypher, dict(params)))
        return 2


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, Any]]]:
    RecordingGraph.queries = []
    monkeypatch.setattr(pagination, "GraphConnection", RecordingGraph)
    yield RecordingGraph.queries


async def test_people_are_paginated(matched: list[dict[str, Any]]) -> None:
    async with client_for(people_app.app) as client:
        response = await client.get("/people", params={"items_by_page": 2})

    assert response.json() == json.loads((EXAMPLES / "response.json").read_text())
    assert matched == [{"skip": 0, "limit": 2, "filters": None}]


async def test_the_serializer_shapes_the_items(matched: list[dict[str, Any]]) -> None:
    async with client_for(serializer.app) as client:
        response = await client.get("/people/labels", params={"current_page": 2})

    page = response.json()
    assert page["items"] == []
    assert page["item_count"] == 3

    async with client_for(serializer.app) as client:
        response = await client.get("/people/labels")

    assert response.json()["items"] == [
        {"label": "Ada (London)"},
        {"label": "Alan (London)"},
        {"label": "Grace (New York)"},
    ]


async def test_employees_go_through_the_relationship(
    graph: list[tuple[str, Any]],
) -> None:
    async with client_for(related.app) as client:
        response = await client.get(
            "/companies/Acme/employees", params={"current_page": 3}
        )

    assert response.json()["item_count"] == 2
    items_query, count_query = graph
    assert [items_query[0], count_query[0]] == cypher_queries("related.cypher")
    assert items_query[1] == {
        "filter_company_name_iexact": "Acme",
        "skip": 20,
        "limit": 10,
    }


async def test_an_empty_relationship_list_filters_the_node_itself(
    graph: list[tuple[str, Any]],
) -> None:
    async with client_for(filtered.app) as client:
        await client.get("/people", params={"city": "london"})

    items_query, _ = graph
    assert [items_query[0]] == cypher_queries("filtered.cypher")
    assert items_query[1] == {
        "filter_person_city_iexact": "london",
        "skip": 0,
        "limit": 10,
    }


async def test_the_documented_defaults(
    matched: list[dict[str, Any]], graph: list[tuple[str, Any]]
) -> None:
    page = await paginate(
        model=Person,
        current_page=1,
        items_by_page=10,
        filters=None,
        serializer=None,
    )
    related_page = await paginate_related(
        model=Person,
        relationships=[WorksFor],
        current_page=1,
        items_by_page=10,
        filters=None,
        ordering=None,
        serializer=None,
    )

    assert page.item_count == 3
    assert related_page.item_count == 2
