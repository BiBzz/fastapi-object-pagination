from neontology import BaseNode, BaseRelationship


class Person(BaseNode):
    __primarylabel__: str = "Person"
    __primaryproperty__: str = "name"

    name: str
    city: str


class Company(BaseNode):
    __primarylabel__: str = "Company"
    __primaryproperty__: str = "name"

    name: str


class WorksFor(BaseRelationship):
    __relationshiptype__: str = "WORKS_FOR"

    source: Person
    target: Company
