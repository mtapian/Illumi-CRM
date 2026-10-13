from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from inventory.infrastructure.contenedor import sembrar_almacen
from sales.infrastructure.contenedor import sembrar_cliente_generico
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol


@pytest.fixture
def empresa_ventas(crear_empresa):
    """Empresa con todo habilitado, una administradora, el almacén "Principal", "Clientes
    varios" y dos productos que se venden: TER-IPA-330 (S/ 12) y TER-IPA-20L (S/ 380)."""
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    lucia = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, lucia.id, date.today())
    sembrar_almacen(empresa.id, lucia.id, date.today())
    sembrar_cliente_generico(empresa.id, lucia.id, date.today())
    with tenant_context(empresa.id):
        und = Unidad.objects.get(abreviatura="UND")
        for sku, precio in (("TER-IPA-330", 12), ("TER-IPA-20L", 380)):
            Producto.objects.create(
                sku=sku,
                nombre=sku,
                unidad=und,
                se_compra=False,
                se_vende=True,
                se_fabrica=True,
                precio_venta=precio,
            )
        yield empresa, actor_de(lucia, date.today())
