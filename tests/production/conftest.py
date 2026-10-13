from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from inventory.infrastructure.contenedor import sembrar_almacen
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol


@pytest.fixture
def empresa_produccion(crear_empresa):
    """Empresa con todo habilitado, una administradora, el almacén "Principal", el granel
    GRA-IPA (en L, se fabrica, vida útil 60 días) y el insumo INS-MALTA (en KG)."""
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    lucia = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, lucia.id, date.today())
    sembrar_almacen(empresa.id, lucia.id, date.today())
    with tenant_context(empresa.id):
        litro, kg = Unidad.objects.get(abreviatura="L"), Unidad.objects.get(abreviatura="KG")
        Producto.objects.create(
            sku="GRA-IPA",
            nombre="IPA a granel",
            unidad=litro,
            se_compra=False,
            se_fabrica=True,
            vida_util_dias=60,
        )
        Producto.objects.create(sku="INS-MALTA", nombre="Malta", unidad=kg, se_compra=True)
        yield empresa, actor_de(lucia, date.today())
