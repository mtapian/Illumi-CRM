"""0004a, T2: la base refuerza las reglas de la compra (RF-COM-04, 11, 13; art. 7.3)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from catalog.infrastructure.models import Producto
from inventory.infrastructure.models import Almacen
from purchasing.infrastructure.models import Compra, CompraLinea, Proveedor

pytestmark = pytest.mark.django_db


@pytest.fixture
def base(empresa_compras):
    proveedor = Proveedor.objects.create(
        tipo_doc="RUC", num_doc="20512345671", razon_social="Maltería del Sur"
    )
    almacen = Almacen.objects.get(nombre="Principal")
    return proveedor, almacen, Producto.objects.get(sku="INS-MALTA")


def compra(proveedor, almacen, numero, doc="FACTURA", serie="F001-1", **kw):
    return Compra.objects.create(
        numero=numero,
        proveedor=proveedor,
        fecha=date.today(),
        almacen=almacen,
        doc_tipo=doc,
        doc_serie_numero=serie,
        igv_pct=D("18"),
        **kw,
    )


def falla(excepcion, crear):
    with transaction.atomic(), pytest.raises(excepcion):
        crear()


def test_documento_unico_entre_compras_activas(base):
    proveedor, almacen, _ = base
    compra(proveedor, almacen, 1)
    falla(IntegrityError, lambda: compra(proveedor, almacen, 2))
    compra(proveedor, almacen, 3, estado="ANULADA")  # una anulada no cuenta (RF-COM-11)
    compra(proveedor, almacen, 4, doc="SIN_DOCUMENTO", serie="")
    compra(proveedor, almacen, 5, doc="SIN_DOCUMENTO", serie="")
    falla(IntegrityError, lambda: compra(proveedor, almacen, 1, serie="F001-2"))  # número


def test_total_es_subtotal_mas_igv_y_finalizada_con_recepcion(base):
    proveedor, almacen, _ = base
    falla(IntegrityError, lambda: compra(proveedor, almacen, 1, subtotal=10, igv=1, total=12))
    falla(IntegrityError, lambda: compra(proveedor, almacen, 2, estado="FINALIZADA"))


def test_costo_cero_solo_en_bonificacion(base):
    proveedor, almacen, malta = base
    c = compra(proveedor, almacen, 1)

    def linea(cantidad="1", costo="1", bonificacion=False):
        return CompraLinea.objects.create(
            compra=c,
            producto=malta,
            cantidad=D(cantidad),
            costo_unitario=D(costo),
            es_bonificacion=bonificacion,
            subtotal=D("0"),
        )

    linea(costo="0", bonificacion=True)
    falla(IntegrityError, lambda: linea(costo="0"))
    falla(IntegrityError, lambda: linea(costo="2", bonificacion=True))
    falla(IntegrityError, lambda: linea(cantidad="0"))


def test_lineas_de_una_compra_finalizada_no_se_cambian(base):
    """RF-COM-13: mientras está Creada o En proceso se editan; después, no."""
    proveedor, almacen, malta = base
    c = compra(proveedor, almacen, 1)
    datos = {"producto": malta, "cantidad": D("1"), "costo_unitario": D("1"), "subtotal": 1}
    linea = CompraLinea.objects.create(compra=c, **datos)
    CompraLinea.objects.filter(pk=linea.pk).update(cantidad=D("2"))
    Compra.objects.filter(pk=c.pk).update(estado="FINALIZADA", fecha_recepcion=date.today())
    falla(DatabaseError, lambda: CompraLinea.objects.filter(pk=linea.pk).update(cantidad=3))
    falla(DatabaseError, lambda: CompraLinea.objects.filter(pk=linea.pk).delete())
    falla(DatabaseError, lambda: CompraLinea.objects.create(compra=c, **datos))
