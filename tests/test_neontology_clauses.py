import pytest
from neontology import BaseNode, BaseRelationship

from fastapi_object_pagination.neontology.clauses import (
    _cypher_relation_to_match_clause,
    _filters_to_where_clause,
    _ordering_to_order_by_clause,
    _postfixes,
    _prefixes,
)

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


async def test_no_filters_gives_an_empty_clause() -> None:
    clause, params = await _filters_to_where_clause(None)

    assert clause == ""
    assert params == {}


async def test_exact_is_the_default_lookup() -> None:
    clause, params = await _filters_to_where_clause({(Person, "name"): "Ada"})

    assert clause == " WHERE person.name = $filter_person_name_exact"
    assert params == {"filter_person_name_exact": "Ada"}


@pytest.mark.parametrize(
    ("lookup", "expected"),
    [
        ("iexact", "toLower(person.name) = toLower($filter_person_name_iexact)"),
        ("contains", "person.name CONTAINS $filter_person_name_contains"),
        ("startswith", "person.name STARTS WITH $filter_person_name_startswith"),
        ("endswith", "person.name ENDS WITH $filter_person_name_endswith"),
        ("gte", "person.name >= $filter_person_name_gte"),
        ("in", "person.name IN $filter_person_name_in"),
    ],
)
async def test_lookups_build_their_cypher_operator(lookup: str, expected: str) -> None:
    clause, _ = await _filters_to_where_clause({(Person, f"name__{lookup}"): "Ada"})

    assert clause == f" WHERE {expected}"


async def test_isnull_does_not_compare_to_a_parameter() -> None:
    clause, _ = await _filters_to_where_clause({(Person, "city__isnull"): True})

    assert clause == " WHERE person.city IS NULL"

    clause, _ = await _filters_to_where_clause({(Person, "city__isnull"): False})

    assert clause == " WHERE person.city IS NOT NULL"


async def test_several_filters_are_joined_with_and() -> None:
    clause, params = await _filters_to_where_clause(
        {(Person, "name"): "Ada", (Person, "city__icontains"): "paris"}
    )

    assert " AND " in clause
    assert len(params) == 2


async def test_a_non_tuple_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="tuples of"):
        await _filters_to_where_clause({"name": "Ada"})  # type: ignore[dict-item]


async def test_relationship_becomes_a_match_clause() -> None:
    clause = await _cypher_relation_to_match_clause(LivesIn)

    assert clause == " MATCH (person:Person)-[:LIVES_IN]-(city:City)"


async def test_ordering_uses_asc_and_desc() -> None:
    clause = await _ordering_to_order_by_clause(Person, ["city", "-name"])

    assert clause == " ORDER BY person.city ASC, person.name DESC"


async def test_prefixes_chain_match_and_where() -> None:
    cypher, params = await _prefixes(Person, [LivesIn], {(City, "name"): "Paris"})

    assert cypher == (
        "MATCH (person:Person)"
        " MATCH (person:Person)-[:LIVES_IN]-(city:City)"
        " WHERE city.name = $filter_city_name_exact"
    )
    assert params == {"filter_city_name_exact": "Paris"}


async def test_postfixes_add_skip_and_limit_as_parameters() -> None:
    cypher, params = await _postfixes(Person, {}, ["-name"], 20, 10)

    assert cypher == " ORDER BY person.name DESC SKIP $skip LIMIT $limit"
    assert params == {"skip": 20, "limit": 10}
