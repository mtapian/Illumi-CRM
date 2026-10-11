from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from inventory.infrastructure.contenedor import sembrar_almacen
from inventory.infrastructure.models import Almacen
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol


@pytest.fixture
def inv(crear_empresa):
    """Empresa con todo habilitado (antes de sembrar los roles, que se recortan a lo
    habilitado), unidades, almacén "Principal", la malta (KG) y la IPA en botella (UND)."""
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    admin = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, admin.id, date.today())
    sembrar_almacen(empresa.id, admin.id, date.today())
    with tenant_context(empresa.id):
        u = {x.abreviatura: x for x in Unidad.objects.all()}
        malta = Producto.objects.create(sku="INS-MALTA", nombre="Malta", unidad=u["KG"])
        ipa = Producto.objects.create(
            sku="TER-IPA-330",
            nombre="IPA 330",
            unidad=u["UND"],
            se_compra=False,
            se_fabrica=True,
            se_vende=True,
            precio_venta=12,
            vida_util_dias=120,
        )
        tour = Producto.objects.create(
            sku="SRV-TOUR",
            nombre="Visita",
            tipo="SERVICIO",
            unidad=u["SERV"],
            se_compra=False,
            se_vende=True,
            precio_venta=30,
        )
        yield {
            "empresa": empresa,
            "admin": admin,
            "malta": malta.id,
            "ipa": ipa.id,
            "tour": tour.id,
            "principal": Almacen.objects.get().id,
        }
