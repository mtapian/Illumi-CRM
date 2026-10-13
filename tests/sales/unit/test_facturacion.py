"""0006b, T1: dominio de facturación y cobranza (RF-VEN-19, 24, 25, 27, 28, 52 a 57)."""

from datetime import date
from decimal import Decimal as D

import pytest

from sales.domain import cobranza as c
from sales.domain import facturacion as f
from sales.domain.errores import CobranzaInvalida, PedidoInvalido

HOY = date(2026, 12, 1)
UMBRAL = D("700.00")


@pytest.mark.parametrize(
    "tipo_doc, comprobante",
    [("RUC", f.FACTURA), ("DNI", f.BOLETA), ("CE", f.BOLETA), ("PAS", f.BOLETA), ("SD", f.BOLETA)],
)
def test_el_comprobante_sale_del_documento_del_cliente(tipo_doc, comprobante):
    """RF-VEN-19 y 24 (RN-VEN-02): Factura con RUC; Boleta en cualquier otro caso."""
    assert f.comprobante_para(tipo_doc) == comprobante


def test_boleta_mayor_al_umbral_a_clientes_varios_se_rechaza():
    """RF-VEN-25 (RN-VEN-03)."""
    with pytest.raises(PedidoInvalido, match="mayores a S/ 700.00 requieren identificar"):
        f.validar_boleta(True, D("720.00"), UMBRAL)
    f.validar_boleta(True, D("700.00"), UMBRAL)  # no supera
    f.validar_boleta(False, D("720.00"), UMBRAL)  # cliente identificado


def test_al_contado_una_cuota_por_el_total_en_la_emision():
    """RF-VEN-19."""
    assert f.cronograma(f.CONTADO, f.BOLETA, (), D("288.00"), HOY) == (f.Cuota(D("288.00"), HOY),)


def test_credito_con_cuotas_validas():
    """RF-VEN-19 y 27."""
    cuotas = (
        f.Cuota(D("144.00"), f.vencimiento_en(HOY, 15)),
        f.Cuota(D("144.00"), f.vencimiento_en(HOY, 30)),
    )
    assert cuotas[1].vencimiento == date(2026, 12, 31)
    assert f.cronograma(f.CREDITO, f.FACTURA, cuotas, D("288.00"), HOY) == cuotas


@pytest.mark.parametrize(
    "comprobante, cuotas, mensaje",
    [
        (f.BOLETA, ((D("288"), 30),), r"requiere factura \(cliente con RUC\)"),
        (f.FACTURA, (), "al menos una cuota"),
        (f.FACTURA, ((D("0"), 30), (D("288"), 30)), "monto mayor a 0"),
        (f.FACTURA, ((D("288"), 0),), "posterior a la emisión"),
        (f.FACTURA, ((D("200"), 30),), r"La suma de las cuotas \(200.00\) .* \(288.00\)"),
    ],
)
def test_credito_invalido(comprobante, cuotas, mensaje):
    """RF-VEN-27 (RN-VEN-08)."""
    filas = tuple(f.Cuota(m, f.vencimiento_en(HOY, d)) for m, d in cuotas)
    with pytest.raises(PedidoInvalido, match=mensaje):
        f.cronograma(f.CREDITO, comprobante, filas, D("288.00"), HOY)


def test_valor_cero_o_negativo_se_rechaza():
    """RF-VEN-28."""
    with pytest.raises(PedidoInvalido, match="TER-IPA-330: el ISC deja el valor en 0"):
        f.validar_valor("TER-IPA-330", D("0.00"))
    f.validar_valor("TER-IPA-330", D("0.01"))


def test_pagos_de_la_venta_directa_suman_el_total():
    """RF-VEN-52."""
    f.validar_pagos_directa([D("200.00"), D("88.00")], D("288.00"))
    with pytest.raises(
        PedidoInvalido, match=r"Los pagos \(300.00\) deben sumar el total \(288.00\)"
    ):
        f.validar_pagos_directa([D("300.00")], D("288.00"))
    with pytest.raises(PedidoInvalido, match="mayor a 0"):
        f.validar_pagos_directa([D("288.00"), D("0")], D("288.00"))


def test_estado_de_la_cobranza():
    """RF-VEN-54 y 56."""
    assert c.estado(D("288.00"), D("100.00")) == c.PENDIENTE
    assert c.estado(D("288.00"), D("288.00")) == c.PAGADA


@pytest.mark.parametrize(
    "estado, monto, saldo, mensaje",
    [
        (c.PENDIENTE, D("300.00"), D("288.00"), r"no superar el saldo \(288.00\)"),
        (c.PENDIENTE, D("0"), D("188.00"), r"mayor a 0 y no superar el saldo \(188.00\)"),
        (c.PAGADA, D("1.00"), D("0.00"), "La cobranza ya está pagada"),
    ],
)
def test_pagos_que_no_se_aceptan(estado, monto, saldo, mensaje):
    """RF-VEN-55 y 57."""
    with pytest.raises(CobranzaInvalida, match=mensaje):
        c.validar_pago(estado, monto, saldo)


def test_pago_valido():
    c.validar_pago(c.PENDIENTE, D("188.00"), D("188.00"))


CUOTAS = (
    f.Cuota(D("144.00"), date(2026, 11, 16)),
    f.Cuota(D("144.00"), date(2026, 12, 16)),
)


def test_monto_vencido_y_proximo_vencimiento():
    """RF-VEN-53: cuotas vencidas − pagos; el próximo, la primera cuota no cubierta."""
    assert c.monto_vencido(CUOTAS, D("100.00"), HOY) == D("44.00")
    assert c.monto_vencido(CUOTAS, D("200.00"), HOY) == D("0")
    assert c.proximo_vencimiento(CUOTAS, D("100.00")) == date(2026, 11, 16)
    assert c.proximo_vencimiento(CUOTAS, D("144.00")) == date(2026, 12, 16)
    assert c.proximo_vencimiento(CUOTAS, D("288.00")) is None


def test_vencida():
    """RF-VEN-53: indicador de una cobranza Pendiente con monto vencido."""
    assert c.vencida(c.PENDIENTE, CUOTAS, D("100.00"), HOY)
    assert not c.vencida(c.PENDIENTE, CUOTAS, D("144.00"), HOY)
    assert not c.vencida(c.PAGADA, CUOTAS, D("288.00"), date(2027, 1, 1))
