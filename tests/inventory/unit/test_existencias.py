"""0003a, T4 a T7: existencias, FEFO, lotes y reversiones (RF-INV-19 a 23, 25, 26;
RN-INV-02 a 07). Todo con `hoy` como parámetro."""

from datetime import date
from decimal import Decimal as D

import pytest

from inventory.domain.errores import (
    AnulacionConConsumoPosterior,
    LoteConOtroVencimiento,
    LoteVencido,
    ServicioSinStock,
    StockInsuficiente,
)
from inventory.domain.existencia import ENTRADA, SALIDA, Existencia, Movimiento, salir
from inventory.domain.fefo import asignar_fefo, orden_fefo
from inventory.domain.lotes import (
    lote_vencido,
    sugerir_vencimiento,
    validar_bien,
    validar_lote_existente,
    validar_salida_de_lote,
)
from inventory.domain.movimientos import hubo_salidas_posteriores, inversos_de, validar_reversion

HOY = date(2026, 11, 1)


def lote(codigo, vence, cantidad, ingreso=date(2026, 1, 1), id_=0):
    return Existencia(D(cantidad), codigo, vence, ingreso, id_, "TER-IPA-330", "Principal")


# --- T4: existencia por almacén y lote (RF-INV-19) ---


def test_salir_no_deja_stock_negativo():
    e = Existencia(D("5"), producto="INS-MALTA", almacen="Principal")
    assert salir(e, D("5")).cantidad == D("0.0000")
    msg = "Stock insuficiente de INS-MALTA en Principal: disponible 5.0000, requerido 6.0000"
    with pytest.raises(StockInsuficiente, match=msg):
        salir(e, D("6"))


# --- T5: vencimiento y FEFO (RF-INV-22, RN-INV-05, 06) ---


def test_el_lote_que_vence_hoy_todavia_sirve():
    assert not lote_vencido(HOY, HOY)
    assert lote_vencido(date(2026, 10, 31), HOY)
    assert not lote_vencido(None, HOY)


def test_fefo_excluye_vencidos_y_reparte_por_vencimiento():
    existencias = [
        lote("IPA-0018", date(2027, 2, 20), "120", id_=3),
        lote("IPA-0012", date(2026, 10, 30), "10", id_=1),
        lote("IPA-0015", date(2026, 12, 15), "48", id_=2),
    ]
    asignado = [(e.lote, c) for e, c in asignar_fefo(existencias, D("60"), HOY, "UND")]
    assert asignado == [("IPA-0015", D("48")), ("IPA-0018", D("12"))]
    with pytest.raises(
        StockInsuficiente, match="Stock disponible insuficiente: 168 UND sin vencer"
    ):
        asignar_fefo(existencias, D("170"), HOY, "UND")


def test_sin_vencimiento_y_sin_lote_al_final():
    """Empate de vencimiento: el más antiguo; sin fecha, del más antiguo al más nuevo; el stock
    sin lote, al final."""
    sin_lote = Existencia(D("5"), id_=9)
    sin_fecha_viejo = lote("A", None, "1", date(2026, 1, 1), 4)
    sin_fecha_nuevo = lote("B", None, "1", date(2026, 6, 1), 5)
    nuevo = lote("C", date(2027, 1, 1), "1", date(2026, 6, 1), 6)
    viejo = lote("D", date(2027, 1, 1), "1", date(2026, 2, 1), 7)
    todas = [sin_lote, sin_fecha_nuevo, nuevo, sin_fecha_viejo, viejo]
    assert [e.lote for e in sorted(todas, key=orden_fefo)] == ["D", "C", "A", "B", None]
    asignado = asignar_fefo(todas, D("6"), HOY, "UND")
    assert [(e.lote, c) for e, c in asignado][-1] == (None, D("2"))


# --- T6: lote vencido y salidas posteriores (RF-INV-21, 23) ---


def test_lote_vencido_solo_sale_por_merma():
    vencido = lote("IPA-0012", date(2026, 10, 30), "10")
    validar_salida_de_lote(vencido, "MERMA", HOY)
    with pytest.raises(
        LoteVencido, match="El lote IPA-0012 está vencido: solo puede salir por merma"
    ):
        validar_salida_de_lote(vencido, "CORRECCION", HOY)


def mov(id_, tipo, almacen=1, revierte=None, cant="1", costo="1"):
    return Movimiento(id_, tipo, D(cant), D(costo), almacen, None, revierte)


def test_salida_posterior_en_otro_almacen_cuenta():
    compra = mov(2, ENTRADA)
    assert not hubo_salidas_posteriores([mov(1, SALIDA), compra, mov(3, ENTRADA)], compra)
    assert hubo_salidas_posteriores([compra, mov(4, SALIDA, almacen=2)], compra)
    # La reversión de otra entrada no consume esta compra.
    assert not hubo_salidas_posteriores([compra, mov(5, SALIDA, revierte=3)], compra)
    with pytest.raises(AnulacionConConsumoPosterior, match="ajuste CORRECCION"):
        validar_reversion([compra, mov(4, SALIDA, almacen=2)], [compra])


# --- T6b: servicios y lotes nuevos (RF-INV-25, 26) ---


def test_servicio_no_lleva_stock():
    validar_bien("BIEN")
    with pytest.raises(ServicioSinStock, match="Un servicio no lleva stock"):
        validar_bien("SERVICIO")


def test_vencimiento_sugerido_por_la_vida_util():
    assert sugerir_vencimiento(HOY, 120) == date(2027, 3, 1)
    assert sugerir_vencimiento(HOY, None) is None


def test_lote_existente_con_otro_vencimiento():
    validar_lote_existente("IPA-0015", date(2026, 12, 15), date(2026, 12, 15))
    validar_lote_existente("IPA-0015", date(2026, 12, 15), None)  # sin indicar: el del lote
    msg = "El lote IPA-0015 ya existe con vencimiento 2026-12-15"
    with pytest.raises(LoteConOtroVencimiento, match=msg):
        validar_lote_existente("IPA-0015", date(2026, 12, 15), date(2027, 1, 31))
    with pytest.raises(LoteConOtroVencimiento, match="ya existe sin vencimiento"):
        validar_lote_existente("A", None, date(2027, 1, 31))


# --- T7: inversos al costo original (RF-INV-20) ---


def test_inversos_usan_el_costo_original():
    movs = [mov(1, ENTRADA, cant="50", costo="5"), mov(2, SALIDA, cant="3", costo="4.333333")]
    inversos = inversos_de(movs)
    assert [(m.tipo, m.cantidad, m.costo_unitario, m.revierte_id) for m in inversos] == [
        (SALIDA, D("50"), D("5"), 1),
        (ENTRADA, D("3"), D("4.333333"), 2),
    ]
    assert all(m.id is None for m in inversos)
