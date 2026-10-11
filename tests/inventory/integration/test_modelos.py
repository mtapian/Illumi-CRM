"""0003a, T8 a T10: modelos con sus restricciones, movimientos inmutables y almacén
"Principal" (RF-INV-01, 17, 19, 20, 24; constitución, art. 4.4 y 7.3)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from inventory.infrastructure.models import Almacen, CostoProducto, Lote, Movimiento, Stock
from shared.domain.tenant import tenant_context
from tenancy.application.sembradores import sembradores
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def base(crear_empresa):
    empresa = crear_empresa()
    admin = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, admin.id, date.today())
    with tenant_context(empresa.id):
        kg = Unidad.objects.get(abreviatura="KG")
        malta = Producto.objects.create(sku="INS-MALTA", nombre="Malta", unidad=kg)
        almacen = Almacen.objects.create(nombre="Principal")
        yield {"empresa": empresa, "admin": admin, "malta": malta, "almacen": almacen}


def falla(excepcion, crear):
    with transaction.atomic(), pytest.raises(excepcion):
        crear()


def test_stock_sin_negativos_y_unico_aun_sin_lote(base):
    """T8, RF-INV-19: una fila por producto, almacén y lote; el stock sin lote también."""
    malta, almacen = base["malta"], base["almacen"]
    Stock.objects.create(producto=malta, almacen=almacen, cantidad=D("5"))
    falla(IntegrityError, lambda: Stock.objects.create(producto=malta, almacen=almacen))
    lote = Lote.objects.create(producto=malta, codigo="M-01", fecha_ingreso=date.today())
    Stock.objects.create(producto=malta, almacen=almacen, lote=lote, cantidad=D("1"))
    Stock.objects.filter(lote=lote).update(cantidad=D("0"))
    falla(IntegrityError, lambda: Stock.objects.filter(lote=lote).update(cantidad=D("-1")))
    falla(
        IntegrityError,
        lambda: Lote.objects.create(producto=malta, codigo="M-01", fecha_ingreso=date.today()),
    )


def test_costo_sin_negativos_y_en_cero_vale_cero(base):
    """T8, RF-INV-24: con cantidad 0 el valor es 0.00; el promedio queda de referencia."""
    malta = base["malta"]
    CostoProducto.objects.create(producto=malta, costo_promedio=D("4.333333"))
    falla(IntegrityError, lambda: CostoProducto.objects.create(producto=malta))
    falla(IntegrityError, lambda: CostoProducto.objects.update(valor_total=D("0.01")))
    falla(
        IntegrityError,
        lambda: CostoProducto.objects.update(cantidad_total=D("1"), valor_total=D("-1")),
    )


def movimiento(base, **kw):
    datos = {
        "tipo": "ENTRADA",
        "motivo": "SALDO_INICIAL",
        "producto": base["malta"],
        "almacen": base["almacen"],
        "cantidad": D("100"),
        "costo_unitario": D("4"),
        "costo_total": D("400"),
        "saldo_cantidad": D("100"),
        "saldo_promedio": D("4"),
        "ref_tipo": "AJUSTE",
        "usuario": base["admin"],
    }
    return Movimiento.objects.create(**datos | kw)


def test_el_kardex_es_inmutable_y_no_se_revierte_dos_veces(base):
    """T9, RF-INV-17 y RF-INV-20."""
    m = movimiento(base)
    falla(DatabaseError, lambda: Movimiento.objects.filter(pk=m.pk).update(cantidad=D("1")))
    falla(DatabaseError, lambda: Movimiento.objects.filter(pk=m.pk).delete())
    movimiento(base, tipo="SALIDA", revierte=m, saldo_cantidad=D("0"))
    falla(IntegrityError, lambda: movimiento(base, tipo="SALIDA", revierte=m))
    falla(IntegrityError, lambda: movimiento(base, cantidad=D("0")))


def test_empresa_nueva_tiene_almacen_principal(crear_empresa):
    """T10, RF-INV-01: el sembrador de 0001a crea "Principal"."""
    empresa = crear_empresa(ruc="20100047218")
    admin = Usuario.objects.create_user("a@b.pe", "x", empresa=empresa)
    sembradores.sembrar(empresa.id, admin.id, date.today())
    with tenant_context(empresa.id):
        assert list(Almacen.objects.values_list("nombre", "activo")) == [("Principal", True)]
