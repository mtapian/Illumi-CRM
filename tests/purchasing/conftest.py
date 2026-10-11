from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol


@pytest.fixture
def empresa_compras(crear_empresa):
    """Empresa con todo habilitado, una administradora y el insumo INS-MALTA (se compra)."""
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    lucia = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, lucia.id, date.today())
    with tenant_context(empresa.id):
        kg = Unidad.objects.get(abreviatura="KG")
        Producto.objects.create(sku="INS-MALTA", nombre="Malta", unidad=kg, se_compra=True)
        yield empresa, actor_de(lucia, date.today())
