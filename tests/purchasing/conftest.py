from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from inventory.infrastructure.contenedor import sembrar_almacen
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import ParametroVigencia, PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol


@pytest.fixture
def empresa_compras(crear_empresa):
    """Empresa con todo habilitado, una administradora, el almacén "Principal" y el insumo
    INS-MALTA (se compra)."""
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    lucia = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, lucia.id, date.today())
    sembrar_almacen(empresa.id, lucia.id, date.today())
    # IGV propio: no depende del valor de plataforma que siembra la migración (los tests con
    # transacciones reales vacían la base al terminar).
    ParametroVigencia.objects.create(
        empresa=empresa, clave="igv_pct", valor=18, vigente_desde=date(2000, 1, 1)
    )
    with tenant_context(empresa.id):
        kg = Unidad.objects.get(abreviatura="KG")
        Producto.objects.create(sku="INS-MALTA", nombre="Malta", unidad=kg, se_compra=True)
        yield empresa, actor_de(lucia, date.today())
