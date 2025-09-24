import pytest
from fastapi_object_pagination.check_optional_dependencies import (
    ORM,
    check_optional_deps,
)


@pytest.mark.neontology
class TestNeontology:
    def test_neontology_backend_correctly_installed(self):
        assert check_optional_deps(ORM.NEONTOLOGY) is None


@pytest.mark.sqlmodel
class TestSQLModel:
    def test_sqlmodel_backend_correctly_installed(self):
        assert check_optional_deps(ORM.SQLMODEL) is None


class TestCommon:
    def test_unsupported_backend_raises_exception(self):
        with pytest.raises(ValueError):
            check_optional_deps("unsupported")
