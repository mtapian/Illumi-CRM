"""0002e, T2: la base refuerza las reglas de impuestos, tasas y producto–impuesto
(RF-CAT-53, 54, 56)."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from catalog.infrastructure.models import Impuesto, ImpuestoTasa, Producto, ProductoImpuesto, Unidad

pytestmark = pytest.mark.django_db


def falla(error, accion):
    with pytest.raises(error), transaction.atomic():
        accion()


def test_nombre_unico_por_empresa_y_tipo_e_isc_solo_de_venta(empresa_catalogo):
    Impuesto.objects.create(nombre="IGV 18%", tipo="VENTA", codigo="IGV")
    Impuesto.objects.create(nombre="IGV 18%", tipo="COMPRA", codigo="IGV")  # otro tipo: válido
    falla(
        IntegrityError,
        lambda: Impuesto.objects.create(nombre="igv 18%", tipo="VENTA", codigo="IGV"),
    )
    falla(
        IntegrityError, lambda: Impuesto.objects.create(nombre="ISC", tipo="COMPRA", codigo="ISC")
    )
    falla(IntegrityError, lambda: Impuesto.objects.create(nombre="X", tipo="AMBOS", codigo="IGV"))
    falla(IntegrityError, lambda: Impuesto.objects.create(nombre="Y", tipo="VENTA", codigo="EXP"))


def test_tasa_unica_por_fecha_no_negativa_y_solo_insercion(empresa_catalogo):
    igv = Impuesto.objects.create(nombre="IGV 18%", tipo="VENTA", codigo="IGV")
    tasa = ImpuestoTasa.objects.create(impuesto=igv, vigente_desde=date(2011, 3, 1), importe=18)
    nueva = {"impuesto": igv, "vigente_desde": date(2011, 3, 1), "importe": Decimal("19")}
    falla(IntegrityError, lambda: ImpuestoTasa.objects.create(**nueva))
    falla(
        IntegrityError,
        lambda: ImpuestoTasa.objects.create(
            **nueva | {"vigente_desde": date(2027, 1, 1), "importe": -1}
        ),
    )
    falla(DatabaseError, lambda: ImpuestoTasa.objects.filter(pk=tasa.pk).update(importe=19))
    falla(DatabaseError, lambda: ImpuestoTasa.objects.filter(pk=tasa.pk).delete())
    falla(IntegrityError, lambda: igv.delete())  # un impuesto con tasas no se borra


def test_un_impuesto_se_asigna_una_sola_vez_a_un_producto(empresa_catalogo):
    igv = Impuesto.objects.create(nombre="IGV 18%", tipo="VENTA", codigo="IGV")
    und = Unidad.objects.get(abreviatura="UND")
    p = Producto.objects.create(
        sku="TER-1", nombre="IPA", unidad=und, se_vende=True, precio_venta=12
    )
    ProductoImpuesto.objects.create(producto=p, impuesto=igv)
    falla(IntegrityError, lambda: ProductoImpuesto.objects.create(producto=p, impuesto=igv))
    assert list(p.impuestos.values_list("nombre", flat=True)) == ["IGV 18%"]


def test_criterio_porcentaje_o_monto_fijo(empresa_catalogo):
    """Enmienda 1: el criterio lo elige el usuario; la base solo admite esos dos."""
    fijo = Impuesto.objects.create(nombre="IGV fijo", tipo="VENTA", codigo="IGV", criterio="FIJO")
    assert fijo.criterio == "FIJO"
    assert (
        Impuesto.objects.create(nombre="IGV", tipo="VENTA", codigo="IGV").criterio == "PORCENTAJE"
    )
    falla(
        IntegrityError,
        lambda: Impuesto.objects.create(nombre="Z", tipo="VENTA", codigo="IGV", criterio="OTRO"),
    )
