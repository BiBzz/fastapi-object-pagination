from typing import cast

import pytest

from fastapi_object_pagination.check_optional_dependencies import (
    ORM,
    check_optional_deps,
)


@pytest.mark.neontology
class TestNeontology:
    def test_neontology_backend_correctly_installed(self) -> None:
        check_optional_deps(ORM.NEONTOLOGY)


@pytest.mark.sqlmodel
class TestSQLModel:
    def test_sqlmodel_backend_correctly_installed(self) -> None:
        check_optional_deps(ORM.SQLMODEL)


class TestCommon:
    def test_unsupported_backend_raises_exception(self) -> None:
        with pytest.raises(ValueError, match="Unsupported ORM"):
            check_optional_deps(cast(ORM, "unsupported"))
