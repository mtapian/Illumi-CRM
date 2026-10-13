"""0004a, T1: líneas, documento, totales y guía de la compra (RF-COM-04, 08, 09, 20, 27)."""

from decimal import Decimal as D

import pytest

from purchasing.domain.compra import (
    LineaCompra,
    numero_compra,
    separa_igv,
    totales,
    validar_documento_compra,
    validar_guia,
    validar_linea,
)
from purchasing.domain.errores import CompraInvalida


def test_linea_con_cantidad_y_costo_positivos():
    validar_linea(D("50"), D("5.00"), False)


@pytest.mark.parametrize(
    ("cantidad", "costo", "bonificacion", "mensaje"),
    [
        ("0", "5", False, "La cantidad debe ser mayor a 0"),
        ("-1", "5", False, "La cantidad debe ser mayor a 0"),
        ("1", "-1", False, "El costo unitario no puede ser negativo"),
        ("1", "0", False, "El costo unitario debe ser mayor a 0; si es una bonificación, márcala"),
        ("1", "2", True, "Una bonificación tiene costo 0"),
    ],
)
def test_linea_invalida(cantidad, costo, bonificacion, mensaje):
    with pytest.raises(CompraInvalida, match=mensaje):
        validar_linea(D(cantidad), D(costo), bonificacion)


def test_bonificacion_con_costo_cero():
    validar_linea(D("5"), D("0"), True)


def test_solo_la_factura_separa_igv():
    assert separa_igv("FACTURA")
    assert not any(separa_igv(d) for d in ("BOLETA", "NOTA_VENTA", "SIN_DOCUMENTO"))


def test_totales_de_la_factura_del_escenario():
    lineas = [LineaCompra(1, D("50"), D("5.00")), LineaCompra(2, D("1200"), D("0.85"))]
    assert totales(lineas, "FACTURA", D("18")) == (D("1270.00"), D("228.60"), D("1498.60"))


def test_boleta_sin_igv():
    assert totales([LineaCompra(1, D("10"), D("5.90"))], "BOLETA", D("18")) == (
        D("59.00"),
        D("0.00"),
        D("59.00"),
    )


def test_redondeo_half_up_por_linea():
    # 3 × 0.335 = 1.005 → 1.01; IGV 1.01 × 18 % = 0.1818 → 0.18; otra igual: 2.02 + 0.36
    lineas = [LineaCompra(1, D("3"), D("0.335")), LineaCompra(1, D("3"), D("0.335"))]
    assert totales(lineas, "FACTURA", D("18")) == (D("2.02"), D("0.36"), D("2.38"))


def test_documento_normalizado_y_sin_documento_sin_serie():
    assert validar_documento_compra("FACTURA", " f001-000845 ", "RUC") == "F001-000845"
    assert validar_documento_compra("SIN_DOCUMENTO", "X", "DNI") == ""


@pytest.mark.parametrize(
    ("tipo", "serie", "proveedor", "mensaje"),
    [
        ("FACTURA", "F001-000010", "DNI", "Una factura requiere un proveedor con RUC"),
        ("BOLETA", " ", "RUC", "Indica la serie y el número del documento"),
        ("RECIBO", "R1", "RUC", "Tipo de documento inválido"),
    ],
)
def test_documento_invalido(tipo, serie, proveedor, mensaje):
    with pytest.raises(CompraInvalida, match=mensaje):
        validar_documento_compra(tipo, serie, proveedor)


def test_guia_de_remision():
    assert validar_guia("") == ""
    assert validar_guia(" t001-00004521 ") == "T001-00004521"
    assert validar_guia("EG01-123") == "EG01-123"
    for mala in ("T1-ABC", "T001-", "T001-123456789", "T0011-1"):
        with pytest.raises(CompraInvalida, match="Guía de remisión inválida"):
            validar_guia(mala)


def test_numero_de_compra():
    assert numero_compra(1) == "C-000001"


def test_igv_por_linea_con_el_impuesto_de_compra_del_producto():
    """RF-CAT-61 (0002e): exonerado 0 %, gravado 18 %; un IGV fijo es cantidad × monto."""
    lineas = [LineaCompra(1, D("10"), D("5.00")), LineaCompra(2, D("10"), D("5.00"))]
    tasas = [("PORCENTAJE", D("0")), ("PORCENTAJE", D("18"))]
    assert totales(lineas, "FACTURA", tasas) == (D("100.00"), D("9.00"), D("109.00"))
    fijo = [("FIJO", D("0.50")), ("PORCENTAJE", D("18"))]
    assert totales(lineas, "FACTURA", fijo) == (D("100.00"), D("14.00"), D("114.00"))
    assert totales(lineas, "BOLETA", tasas) == (D("100.00"), D("0.00"), D("100.00"))
