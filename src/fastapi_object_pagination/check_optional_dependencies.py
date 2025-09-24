from enum import Enum
from importlib.metadata import PackageNotFoundError, version


class ORM(str, Enum):
    NEONTOLOGY = "neontology"
    SQLMODEL = "sqlmodel"


def check_optional_deps(orm: ORM) -> None:
    try:
        if orm == ORM.NEONTOLOGY:
            version(ORM.NEONTOLOGY)
        elif orm == ORM.SQLMODEL:
            version(ORM.SQLMODEL)
        else:
            raise ValueError(
                f"Unsupported ORM: {orm}"
                f"FastAPI Object Pagination only supports 'neontology' and 'sqlmodel'"
            )
    except PackageNotFoundError as e:
        raise ImportError(
            f"ORM '{orm}' need extra dependencies."
            f"Please run : uv add 'fastapi-object-pagination[{orm}]'"
        ) from e
