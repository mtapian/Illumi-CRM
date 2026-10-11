"""0003b, T1 a T3: reglas de los ajustes de inventario (RF-INV-08, 09, 11, 12, 27, 29)."""

from datetime import date
from decimal import Decimal as D

import pytest

from inventory.domain.ajuste import (
    costo_de_entrada_ajuste,
    diferencia_conteo,
    validar_ajuste,
    validar_saldo_inicial,
)
from inventory.domain.errores import AjusteInvalido, CostoRequerido, LoteVencido
from inventory.domain.existencia import Existencia
from inventory.domain.lotes import validar_salida_de_lote

PROMEDIO = D("4.333333")


@pytest.mark.parametrize(
    ("tipo", "ingresado", "promedio", "esperado"),
    [
        ("SALDO_INICIAL", D("4.1"), None, D("4.1")),
        ("CONTEO", None, PROMEDIO, PROMEDIO),
        ("CORRECCION", None, PROMEDIO, PROMEDIO),
        ("CORRECCION", D("5"), PROMEDIO, D("5")),
        ("CONTEO", D("6"), None, D("6")),  # nunca tuvo costo: usa el ingresado
    ],
)
def test_costo_de_entrada_por_tipo(tipo, ingresado, promedio, esperado):
    """T1, RF-INV-08: tabla de costos por tipo de ajuste."""
    assert costo_de_entrada_ajuste(tipo, ingresado, promedio) == esperado


def test_entrada_al_promedio_sin_costo_previo_exige_costo():
    """T1, RF-INV-27."""
    with pytest.raises(CostoRequerido, match="nunca tuvo costo: ingresa el costo unitario"):
        costo_de_entrada_ajuste("CONTEO", None, None)


def test_saldo_inicial_y_conteo():
    """T2, RF-INV-09 y RF-INV-11."""
    validar_saldo_inicial(D("4"), tiene_movimientos=False)
    for costo in (None, D("0")):
        with pytest.raises(AjusteInvalido, match="requiere un costo unitario mayor a 0"):
            validar_saldo_inicial(costo, tiene_movimientos=False)
    with pytest.raises(AjusteInvalido, match="solo sirve para la apertura"):
        validar_saldo_inicial(D("4"), tiene_movimientos=True)
    assert diferencia_conteo(D("1500"), D("1500")) == 0
    assert diferencia_conteo(D("1500"), D("1420")) == D("-80")


def test_motivo_y_destino():
    """T2, RF-INV-08 y RF-INV-12."""
    validar_ajuste("MERMA", "Saco roto", 1, None)
    validar_ajuste("TRANSFERENCIA", "Al taproom", 1, 2)
    with pytest.raises(AjusteInvalido, match="El motivo es obligatorio"):
        validar_ajuste("MERMA", "  ", 1, None)
    with pytest.raises(AjusteInvalido, match="almacén destino distinto del origen"):
        validar_ajuste("TRANSFERENCIA", "x", 1, 1)
    with pytest.raises(AjusteInvalido, match="almacén destino distinto del origen"):
        validar_ajuste("TRANSFERENCIA", "x", 1, None)
    with pytest.raises(AjusteInvalido, match="Solo una transferencia tiene almacén destino"):
        validar_ajuste("MERMA", "x", 1, 2)
    with pytest.raises(AjusteInvalido, match="Tipo de ajuste desconocido"):
        validar_ajuste("REGALO", "x", 1, None)


def test_lote_vencido_sale_por_conteo_y_transferencia():
    """T3, RF-INV-29 (ajusta RF-INV-23)."""
    vencido = Existencia(D("10"), "IPA-0012", date(2026, 10, 30))
    hoy = date(2026, 11, 1)
    for motivo in ("MERMA", "CONTEO", "TRANSFERENCIA"):
        validar_salida_de_lote(vencido, motivo, hoy)
    for motivo in ("VENTA", "CONSUMO_OP", "CORRECCION"):
        with pytest.raises(LoteVencido):
            validar_salida_de_lote(vencido, motivo, hoy)
