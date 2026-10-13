"""0006a, T6 y T7: dominio del pedido (RF-VEN-06 a 08, 11, 14 a 16, 37, 45, 48)."""

from datetime import date
from decimal import Decimal as D

import pytest

from sales.domain import pedido as p
from sales.domain.errores import PedidoInvalido

HOY = date(2026, 11, 20)


@pytest.mark.parametrize(
    "estado, accion, nuevo",
    [
        (p.CREADO, "editar", p.CREADO),
        (p.CREADO, "aprobar", p.APROBADO),
        (p.APROBADO, "editar_fecha", p.APROBADO),
        (p.APROBADO, "facturar", p.FACTURADO),
        (p.FACTURADO, "entregar", p.ENTREGADO),
        (p.CREADO, "cancelar", p.CANCELADO),
        (p.APROBADO, "cancelar", p.CANCELADO),
    ],
)
def test_transiciones(estado, accion, nuevo):
    assert p.transicion(estado, accion) == nuevo


@pytest.mark.parametrize(
    "estado, accion, mensaje",
    [
        (
            p.APROBADO,
            "editar",
            "El pedido está aprobado: cancélalo y crea otro para cambiar sus líneas",
        ),
        (p.FACTURADO, "cancelar", "El pedido está facturado"),
        (p.CREADO, "facturar", "El pedido debe estar aprobado"),
        (p.CANCELADO, "aprobar", "El pedido está cancelado"),
        (p.APROBADO, "aprobar", "El pedido ya está aprobado"),
    ],
)
def test_transiciones_rechazadas(estado, accion, mensaje):
    """RF-VEN-11 y 16."""
    with pytest.raises(PedidoInvalido, match=mensaje):
        p.transicion(estado, accion)


def test_lineas_y_total():
    """RF-VEN-06, 48: total = Σ cantidad × precio, half-up por línea."""
    lineas = [p.LineaPedido(1, D("60"), D("12")), p.LineaPedido(2, D("2"), D("380"))]
    assert p.total(lineas) == D("1480.00")
    assert p.total([p.LineaPedido(1, D("0.3333"), D("10.05"))]) == D("3.35")
    p.validar_lineas(lineas)
    with pytest.raises(PedidoInvalido, match="Un producto está repetido en el pedido"):
        p.validar_lineas(lineas + [p.LineaPedido(1, D("1"), D("12"))])
    with pytest.raises(PedidoInvalido, match="La cantidad debe ser mayor a 0"):
        p.validar_lineas([p.LineaPedido(1, D("0"), D("12"))])
    with pytest.raises(PedidoInvalido, match="El precio debe ser mayor a 0"):
        p.validar_lineas([p.LineaPedido(1, D("1"), D("0"))])
    with pytest.raises(PedidoInvalido, match="El pedido no tiene líneas"):
        p.validar_lineas([], para_aprobar=True)


def test_faltante_e_indicadores():
    """RF-VEN-15, 45, 46."""
    assert p.faltante(D("60"), D("48"), False) == D("12")
    assert p.faltante(D("10"), D("48"), False) == D("0")
    assert p.faltante(D("5"), D("0"), True) == D("0")  # servicio: sin stock
    assert p.indicadores(p.APROBADO, date(2026, 11, 15), [D("0")], HOY) == [
        "Atrasado",
        "Listo para facturar",
    ]
    assert p.indicadores(p.CREADO, date(2026, 11, 25), [D("1")], HOY) == ["Quiebre de stock"]
    assert p.indicadores(p.ENTREGADO, date(2026, 11, 15), [D("1")], HOY) == []
    assert p.indicadores(p.FACTURADO, date(2026, 11, 15), [], HOY) == ["Atrasado"]
    assert p.numero_pedido(12) == "P-000012"
