from fastapi import FastAPI

from fastapi_object_pagination import Page
from fastapi_object_pagination.neontology import paginate_related

from .models import Person

app = FastAPI()


@app.get("/people")
async def list_people(
    city: str, current_page: int = 1, items_by_page: int = 10
) -> Page[Person]:
    return await paginate_related(
        model=Person,
        relationships=[],
        current_page=current_page,
        items_by_page=items_by_page,
        filters={(Person, "city__iexact"): city},
        ordering=["name"],
    )
