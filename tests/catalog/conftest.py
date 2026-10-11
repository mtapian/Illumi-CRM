from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol


@pytest.fixture
def empresa_catalogo(crear_empresa):
    """Empresa con todo habilitado, sus unidades y una administradora; deja el tenant fijado."""
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    lucia = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, lucia.id, date.today())
    with tenant_context(empresa.id):
        yield empresa, actor_de(lucia, date.today())
