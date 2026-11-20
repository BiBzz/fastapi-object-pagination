from fastapi import FastAPI
from pydantic import BaseModel

from fastapi_object_pagination import Page
from fastapi_object_pagination.neontology import paginate

from .models import Person

app = FastAPI()


class PersonOut(BaseModel):
    label: str


def to_person_out(person: Person) -> PersonOut:
    return PersonOut(label=f"{person.name} ({person.city})")


@app.get("/people/labels")
async def list_labels(
    current_page: int = 1, items_by_page: int = 10
) -> Page[PersonOut]:
    return await paginate(
        model=Person,
        current_page=current_page,
        items_by_page=items_by_page,
        serializer=to_person_out,
    )
