"""TenantContext (plan 0000 §4): sin tenant explícito no hay acceso a datos de negocio."""

import pytest

from shared.domain.tenant import TenantNoDefinido, empresa_actual, tenant_context


def test_sin_tenant_lanza_error():
    with pytest.raises(TenantNoDefinido):
        empresa_actual()


def test_tenant_context_fija_y_restaura_la_empresa():
    with tenant_context(7):
        assert empresa_actual() == 7
        with tenant_context(9):
            assert empresa_actual() == 9
        assert empresa_actual() == 7
    with pytest.raises(TenantNoDefinido):
        empresa_actual()
