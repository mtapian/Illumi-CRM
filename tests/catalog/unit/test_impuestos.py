"""0002e, T1: impuesto, tasa, impuestos del producto y desglose de una línea
(RF-CAT-53, 54, 57 a 59)."""

from datetime import date
from decimal import Decimal

import pytest

from catalog.domain.errores import ImpuestoInvalido
from catalog.domain.impuestos import (
    COMPRA,
    EXO,
    FIJO,
    IGV,
    INA,
    ISC,
    PORCENTAJE,
    VENTA,
    Impuesto,
    criterio_sugerido,
    desglose_linea,
    validar_impuesto,
    validar_impuestos,
    validar_tasa,
)

IGV_V, EXO_V, INA_V, ISC_V = (Impuesto(VENTA, c) for c in (IGV, EXO, INA, ISC))
IGV_C, EXO_C = Impuesto(COMPRA, IGV), Impuesto(COMPRA, EXO)
HOY = date(2027, 1, 1)


def pct(importe):
    return PORCENTAJE, Decimal(importe)


def fijo(importe):
    return FIJO, Decimal(importe)


# RF-CAT-53
def test_el_isc_es_solo_un_impuesto_de_venta():
    validar_impuesto(VENTA, ISC)
    validar_impuesto(COMPRA, IGV)
    with pytest.raises(ImpuestoInvalido, match="El ISC es solo un impuesto de venta"):
        validar_impuesto(COMPRA, ISC)


@pytest.mark.parametrize(("tipo", "codigo"), [("AMBOS", IGV), (VENTA, "ICBPER")])
def test_tipo_y_codigo_fuera_del_mvp_se_rechazan(tipo, codigo):
    with pytest.raises(ImpuestoInvalido):
        validar_impuesto(tipo, codigo)


# RF-CAT-54
def test_tasa_valida():
    validar_tasa(IGV, Decimal("18"), [date(2011, 3, 1)], HOY)
    validar_tasa(ISC, Decimal("0.8283"), [], HOY)
    validar_tasa(EXO, Decimal("0"), [], HOY)


@pytest.mark.parametrize(
    ("codigo", "importe", "existentes", "mensaje"),
    [
        (EXO, Decimal("18"), [], "Un impuesto exonerado o inafecto tiene tasa 0"),
        (INA, Decimal("0.01"), [], "Un impuesto exonerado o inafecto tiene tasa 0"),
        (IGV, Decimal("-1"), [], "La tasa no puede ser negativa"),
        (IGV, Decimal("18"), [HOY], "Ya hay una tasa del impuesto en esa fecha"),
        (ISC, Decimal("0.82831"), [], "La tasa admite hasta 4 decimales"),
    ],
)
def test_tasa_invalida(codigo, importe, existentes, mensaje):
    with pytest.raises(ImpuestoInvalido, match=mensaje):
        validar_tasa(codigo, importe, existentes, HOY)


# RF-CAT-57 y 58
@pytest.mark.parametrize(
    ("tipo", "impuestos", "es_servicio"),
    [
        (VENTA, [IGV_V], False),
        (VENTA, [EXO_V, ISC_V], False),
        (VENTA, [INA_V], True),
        (COMPRA, [EXO_C], False),
    ],
)
def test_impuestos_del_producto_validos(tipo, impuestos, es_servicio):
    validar_impuestos(tipo, impuestos, es_servicio)


AFECTACION = "El producto debe tener un impuesto de IGV, exonerado o inafecto"


@pytest.mark.parametrize(
    ("tipo", "impuestos", "es_servicio", "mensaje"),
    [
        (VENTA, [ISC_V], False, AFECTACION),
        (VENTA, [IGV_V, EXO_V], False, AFECTACION),
        (VENTA, [], False, AFECTACION),
        (COMPRA, [IGV_C, Impuesto(COMPRA, INA)], False, AFECTACION),
        (VENTA, [IGV_V, ISC_V], True, "Un servicio no lleva ISC"),
        (VENTA, [IGV_V, ISC_V, ISC_V], False, "Un producto lleva a lo sumo un ISC"),
        (COMPRA, [IGV_V], False, "Un impuesto de venta no va en los impuestos de compra"),
        (VENTA, [IGV_C], False, "Un impuesto de compra no va en los impuestos de venta"),
    ],
)
def test_impuestos_del_producto_invalidos(tipo, impuestos, es_servicio, mensaje):
    with pytest.raises(ImpuestoInvalido, match=mensaje):
        validar_impuestos(tipo, impuestos, es_servicio)


# RF-CAT-59: ISC primero, IGV sobre valor + ISC; precio con impuestos incluidos
def test_desglose_gravado_con_isc_ejemplo_de_0006b():
    d = desglose_linea(Decimal("288.00"), Decimal("24"), pct("18"), fijo("0.8283"))
    assert (d.valor, d.isc, d.igv) == (Decimal("224.19"), Decimal("19.88"), Decimal("43.93"))


def test_desglose_exonerado_sin_isc():
    d = desglose_linea(Decimal("50.00"), Decimal("1"), pct("0"))
    assert (d.valor, d.isc, d.igv) == (Decimal("50.00"), Decimal("0.00"), Decimal("0.00"))


def test_desglose_exonerado_con_isc_respuesta_del_contador():
    d = desglose_linea(Decimal("288.00"), Decimal("24"), pct("0"), fijo("0.8283"))
    assert (d.valor, d.isc, d.igv) == (Decimal("268.12"), Decimal("19.88"), Decimal("0.00"))


def test_desglose_gravado_sin_isc_cuadra_al_centimo():
    d = desglose_linea(Decimal("10.00"), Decimal("1"), pct("18"))
    assert (d.valor, d.isc, d.igv) == (Decimal("8.47"), Decimal("0.00"), Decimal("1.53"))
    assert d.valor + d.isc + d.igv == Decimal("10.00")


# Enmienda 1 (PO, 2026-10-12): cada impuesto elige porcentaje o monto fijo
def test_desglose_isc_porcentual_ejemplo_de_la_spec():
    d = desglose_linea(Decimal("100.00"), Decimal("1"), pct("18"), pct("25"))
    assert (d.valor, d.isc, d.igv) == (Decimal("67.80"), Decimal("16.95"), Decimal("15.25"))


def test_desglose_afectacion_en_monto_fijo():
    """IGV fijo de S/ 1.00 por unidad: 10 unidades a 5.00 → valor 40.00, IGV 10.00."""
    d = desglose_linea(Decimal("50.00"), Decimal("10"), fijo("1.00"))
    assert (d.valor, d.isc, d.igv) == (Decimal("40.00"), Decimal("0.00"), Decimal("10.00"))


def test_criterio_sugerido_y_validado():
    assert [criterio_sugerido(c) for c in (IGV, EXO, INA, ISC)] == [PORCENTAJE] * 3 + [FIJO]
    validar_impuesto(VENTA, IGV, FIJO)  # el cliente lo decide
    with pytest.raises(ImpuestoInvalido, match="El criterio es porcentaje o monto fijo"):
        validar_impuesto(VENTA, IGV, "OTRO")
