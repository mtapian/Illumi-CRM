"""0002c, T1, T2 y T6: tarifa aplicable, ISC de una línea y contenido obligatorio
(RF-CAT-23 a 27; RN-CAT-10)."""

from datetime import date
from decimal import Decimal

import pytest

from catalog.domain.errores import ProductoInvalido
from catalog.domain.isc import Tarifa, contenido_sugerido, isc_linea, tarifa_aplicable
from catalog.domain.producto import DatosProducto, validar_producto
from catalog.domain.tipos import TipoProducto as T

TARIFAS = [Tarifa(date(2024, 7, 1), Decimal("2.51")), Tarifa(date(2027, 1, 1), Decimal("2.70"))]


def test_tarifa_aplicable_antes_el_dia_y_despues_del_cambio():
    assert tarifa_aplicable(TARIFAS, date(2026, 12, 31)).monto_por_litro == Decimal("2.51")
    assert tarifa_aplicable(TARIFAS, date(2027, 1, 1)).monto_por_litro == Decimal("2.70")
    assert tarifa_aplicable(TARIFAS, date(2027, 1, 2)).monto_por_litro == Decimal("2.70")
    assert tarifa_aplicable(TARIFAS, date(2024, 6, 30)) is None


def test_isc_de_una_linea():
    assert isc_linea(Decimal("24"), Decimal("0.33"), TARIFAS[0]) == Decimal("19.88")
    assert isc_linea(Decimal("10"), Decimal("0.33"), None) == Decimal("0.00")


def test_un_bien_que_se_vende_con_isc_requiere_contenido_en_litros():
    datos = DatosProducto(
        "MER-CERV",
        "Cerveza de terceros",
        T.BIEN,
        "UND",
        se_vende=True,
        precio_venta=Decimal("8"),
        isc_sistema="ESPECIFICO",
        isc_codigo_tipo_sistema="02",
    )
    with pytest.raises(ProductoInvalido, match="requiere el contenido en litros por unidad"):
        validar_producto(datos)


def test_isc_solo_sistema_especifico_y_con_codigo():
    """RF-CAT-23, 45: en el MVP solo el Sistema Específico; el código va al comprobante."""
    base = dict(
        sku="X",
        nombre="X",
        tipo=T.BIEN,
        unidad="UND",
        se_vende=True,
        precio_venta=Decimal("8"),
        contenido_litros=Decimal("0.33"),
    )
    with pytest.raises(ProductoInvalido, match="Sistema Específico"):
        validar_producto(
            DatosProducto(**base, isc_sistema="AL_VALOR", isc_codigo_tipo_sistema="01")
        )
    with pytest.raises(ProductoInvalido, match="código de tipo de sistema"):
        validar_producto(DatosProducto(**base, isc_sistema="ESPECIFICO"))
    d = validar_producto(
        DatosProducto(**base, isc_sistema="ESPECIFICO", isc_codigo_tipo_sistema="02")
    )
    assert d.afecto_isc


def test_contenido_sugerido_desde_la_receta():
    """RF-CAT-45: suma de los componentes medidos en L."""
    receta = ((1, Decimal("0.33")), (2, Decimal("1")))
    assert contenido_sugerido(receta, {1: "L", 2: "UND"}) == Decimal("0.3300")
    assert contenido_sugerido(receta, {1: "KG", 2: "UND"}) is None
