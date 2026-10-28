from typing import Any

import pytest
from neontology import BaseNode, BaseRelationship
from pydantic import BaseModel

from fastapi_object_pagination.neontology import pagination
from fastapi_object_pagination.neontology.pagination import paginate, paginate_related

pytestmark = pytest.mark.neontology


class Person(BaseNode):
    __primarylabel__: str = "Person"
    __primaryproperty__: str = "name"

    name: str
    city: str


class City(BaseNode):
    __primarylabel__: str = "City"
    __primaryproperty__: str = "name"

    name: str


class LivesIn(BaseRelationship):
    __relationshiptype__: str = "LIVES_IN"

    source: Person
    target: City


class PersonSummary(BaseModel):
    label: str


def to_summary(person: Person) -> PersonSummary:
    return PersonSummary(label=f"{person.name} ({person.city})")


PEOPLE = [
    Person(name="Ada", city="London"),
    Person(name="Grace", city="New York"),
    Person(name="Alan", city="London"),
]


@pytest.fixture
def matched_nodes(monkeypatch: pytest.MonkeyPatch) -> list[Person]:
    def get_count(cls: type[Person], filters: Any = None) -> int:
        return len(PEOPLE)

    def match_nodes(
        cls: type[Person],
        skip: int = 0,
        limit: int | None = None,
        filters: Any = None,
    ) -> list[Person]:
        end = len(PEOPLE) if limit is None else skip + limit
        return PEOPLE[skip:end]

    monkeypatch.setattr(Person, "get_count", classmethod(get_count))
    monkeypatch.setattr(Person, "match_nodes", classmethod(match_nodes))
    return PEOPLE


async def test_paginate_returns_the_nodes_themselves(
    matched_nodes: list[Person],
) -> None:
    page = await paginate(Person, current_page=1, items_by_page=2)

    assert [person.name for person in page.items] == ["Ada", "Grace"]
    assert all(isinstance(item, Person) for item in page.items)
    assert page.item_count == 3
    assert page.page_count == 2
    assert page.next_page_url == "?current_page=2&items_by_page=2"


async def test_serializer_replaces_the_items(matched_nodes: list[Person]) -> None:
    page = await paginate(
        Person, current_page=1, items_by_page=2, serializer=to_summary
    )

    assert [item.label for item in page.items] == ["Ada (London)", "Grace (New York)"]
    assert all(isinstance(item, PersonSummary) for item in page.items)


async def test_serializer_leaves_the_counts_alone(
    matched_nodes: list[Person],
) -> None:
    plain = await paginate(Person, current_page=2, items_by_page=2)
    serialized = await paginate(
        Person, current_page=2, items_by_page=2, serializer=to_summary
    )

    assert serialized.item_count == plain.item_count
    assert serialized.page_count == plain.page_count
    assert serialized.previous_page_url == plain.previous_page_url
    assert serialized.next_page_url is None


class _StubGraphConnection:
    def evaluate_query(self, cypher: str, params: Any, node_classes: Any) -> Any:
        class _Result:
            nodes = PEOPLE[:2]

        return _Result()

    def evaluate_query_single(self, cypher: str, params: Any) -> int:
        return len(PEOPLE)


@pytest.fixture
def stub_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pagination, "GraphConnection", _StubGraphConnection)


async def test_paginate_related_serializes_too(stub_graph: None) -> None:
    page = await paginate_related(
        Person, [LivesIn], current_page=1, items_by_page=2, serializer=to_summary
    )

    assert [item.label for item in page.items] == ["Ada (London)", "Grace (New York)"]
    assert page.item_count == 3


async def test_paginate_related_without_a_serializer(stub_graph: None) -> None:
    page = await paginate_related(Person, [LivesIn], current_page=1, items_by_page=2)

    assert all(isinstance(item, Person) for item in page.items)
