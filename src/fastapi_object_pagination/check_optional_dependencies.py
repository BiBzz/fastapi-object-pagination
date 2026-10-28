from enum import Enum
from importlib.metadata import PackageNotFoundError, version


class ORM(str, Enum):
    NEONTOLOGY = "neontology"
    SQLMODEL = "sqlmodel"


def check_optional_deps(orm: ORM) -> None:
    try:
        if orm == ORM.NEONTOLOGY:
            version(ORM.NEONTOLOGY.value)
        elif orm == ORM.SQLMODEL:
            version(ORM.SQLMODEL.value)
        else:
            raise ValueError(
                f"Unsupported ORM: {orm!r}. FastAPI Object Pagination only supports "
                f"'neontology' and 'sqlmodel'."
            )
    except PackageNotFoundError as error:
        raise ImportError(
            f"ORM '{orm.value}' needs extra dependencies. "
            f"Please run: uv add 'fastapi-object-pagination[{orm.value}]'"
        ) from error
