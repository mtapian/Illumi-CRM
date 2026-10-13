"""0005a, T1: dominio de la orden de producción (RF-PRD-14, 15, 33, 37, 38, 41, 42, 44, 46, 47)."""

from datetime import date
from decimal import Decimal as D

import pytest

from production.domain import op
from production.domain.errores import OpInvalida

HOY = date(2026, 10, 12)
ESTADOS = {
    1: ("BIEN", True, "INS-MALTA"),
    2: ("BIEN", True, "ENV-BOT"),
    3: ("SERVICIO", True, "MAQ"),
}
ESTADOS |= {4: ("BIEN", False, "VIEJO")}


@pytest.mark.parametrize(
    "estado, accion, nuevo",
    [
        (op.CREADA, "editar", op.CREADA),
        (op.EN_PROCESO, "editar", op.EN_PROCESO),
        (op.CREADA, "en_proceso", op.EN_PROCESO),
        (op.EN_PROCESO, "finalizar", op.FINALIZADA),
        (op.CREADA, "anular", op.ANULADA),
        (op.EN_PROCESO, "anular", op.ANULADA),
    ],
)
def test_transiciones_permitidas(estado, accion, nuevo):
    assert op.transicion(estado, accion) == nuevo


@pytest.mark.parametrize(
    "estado, accion, mensaje",
    [
        (op.FINALIZADA, "anular", "La OP está finalizada: corrígela con un ajuste de inventario"),
        (op.CREADA, "finalizar", "La OP debe estar en proceso para finalizarla"),
        (op.ANULADA, "editar", "La OP está anulada"),
        (op.FINALIZADA, "editar", "La OP está finalizada"),
        (op.EN_PROCESO, "en_proceso", "La OP ya está en proceso"),
    ],
)
def test_transiciones_rechazadas(estado, accion, mensaje):
    """RF-PRD-18, 33."""
    with pytest.raises(OpInvalida, match=mensaje):
        op.transicion(estado, accion)


def test_copiar_receta_escala_con_4_decimales():
    """RF-PRD-37: por consumir = cantidad por unidad × cantidad de la OP."""
    receta = ((1, D("0.2")), (2, D("0.0417")), (3, D("0.33333")))
    componentes = op.copiar_receta(receta, D("500"))
    assert [(c.producto_id, c.por_consumir) for c in componentes] == [
        (1, D("100.0000")),
        (2, D("20.8500")),
        (3, D("166.6650")),
    ]


@pytest.mark.parametrize(
    "componentes, mensaje",
    [
        ([op.Componente(9, D("1"))], "Un producto no puede ser componente de sí mismo"),
        ([op.Componente(1, D("1")), op.Componente(1, D("2"))], "Un componente está repetido"),
        ([op.Componente(4, D("1"))], "El componente VIEJO no existe o está inactivo"),
        ([op.Componente(1, D("-1"))], "La cantidad de INS-MALTA no puede ser negativa"),
        ([op.Componente(3, D("1"))], "Indica el costo del servicio MAQ"),
        ([op.Componente(1, D("1"), D("5"))], "Solo un servicio lleva costo"),
    ],
)
def test_componentes_invalidos(componentes, mensaje):
    """RF-PRD-38, 44."""
    with pytest.raises(OpInvalida, match=mensaje):
        op.validar_componentes(9, componentes, ESTADOS)


def test_componentes_validos_con_servicio():
    op.validar_componentes(
        9, [op.Componente(1, D("1")), op.Componente(3, D("1"), D("80"))], ESTADOS
    )


def test_receta_desde_la_op():
    """RF-PRD-38: por unidad = por consumir / cantidad de la OP; sin los de cantidad 0."""
    componentes = [op.Componente(1, D("100")), op.Componente(2, D("0")), op.Componente(3, D("1"))]
    assert op.receta_desde_op(componentes, D("500")) == ((1, D("0.2000")), (3, D("0.0020")))


@pytest.mark.parametrize(
    "producida, motivo, n, fin, mensaje",
    [
        (D("0"), "", 4, HOY, "Indica el motivo del lote perdido"),
        (D("-1"), "", 4, HOY, "La cantidad producida no puede ser negativa"),
        (D("10"), "", 0, HOY, "La OP no tiene componentes"),
        (D("10"), "", 4, date(2026, 10, 13), "La fecha de fin no puede ser futura"),
    ],
)
def test_finalizacion_invalida(producida, motivo, n, fin, mensaje):
    """RF-PRD-15, 41, 47."""
    with pytest.raises(OpInvalida, match=mensaje):
        op.validar_finalizacion(producida, motivo, n, fin, HOY)


def test_lote_perdido_con_motivo_es_valido():
    op.validar_finalizacion(D("0"), "Contaminación", 4, HOY, HOY)


def test_faltantes_de_todos_los_componentes():
    """RF-PRD-09: indica cada faltante."""
    assert op.faltantes({"A": D("5"), "B": D("2")}, {"A": D("5"), "B": D("3")}) is None
    with pytest.raises(OpInvalida, match="Stock insuficiente: A faltan 1.0000; C faltan 2.0000"):
        op.validar_stock({"A": D("6"), "B": D("1"), "C": D("2")}, {"A": D("5"), "B": D("3")})


def test_costos_del_ejemplo_de_la_spec():
    """RF-PRD-41: (componentes + servicios + indirecto) / producida, a 6 decimales."""
    granel = op.costo_total([D("408"), D("60"), D("180"), D("150")], [], D("52"))
    assert (granel, op.costo_unitario(granel, D("425"))) == (D("850.00"), D("2.000000"))
    botella = op.costo_total([D("680"), D("850"), D("50"), D("200"), D("100.08")], [], D("0"))
    assert op.costo_unitario(botella, D("1000")) == D("1.880080")
    assert op.costo_total([D("10")], [D("80")], D("0")) == D("90.00")
    assert op.costo_unitario(D("790"), D("0")) is None  # lote perdido


def test_merma_y_rendimiento():
    """RF-PRD-42 y 14."""
    assert op.merma(D("100"), D("102")) == D("2.0000")
    assert op.merma(D("10"), D("9.5")) == D("-0.5000")
    assert op.rendimiento(D("500"), D("425")) == D("85.00")
    assert op.excede(D("500"), D("510")) and not op.excede(D("500"), D("500"))


def test_lote_sugerido():
    """RF-PRD-46: el del único componente con un solo lote; si no, SKU y correlativo."""
    assert op.sugerir_lote({1: {"IPA-0020"}, 2: set()}, "TER-IPA-330", 1) == "IPA-0020"
    assert op.sugerir_lote({1: {"IPA-0020", "IPA-0021"}}, "TER-IPA-330", 3) == "TER-IPA-330-0003"
    assert op.sugerir_lote({1: {"A"}, 2: {"B"}}, "GRA-IPA", 12) == "GRA-IPA-0012"
    assert op.sugerir_lote({}, "GRA-IPA", 1) == "GRA-IPA-0001"
