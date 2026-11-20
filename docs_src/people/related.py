from fastapi import FastAPI

from fastapi_object_pagination import Page
from fastapi_object_pagination.neontology import paginate_related

from .models import Company, Person, WorksFor

app = FastAPI()


@app.get("/companies/{company}/employees")
async def list_employees(
    company: str, current_page: int = 1, items_by_page: int = 10
) -> Page[Person]:
    return await paginate_related(
        model=Person,
        relationships=[WorksFor],
        current_page=current_page,
        items_by_page=items_by_page,
        filters={(Company, "name__iexact"): company},
        ordering=["name"],
    )
