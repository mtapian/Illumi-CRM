"""0003c, T1: alertas de stock bajo y lotes por vencer (RF-INV-14, RF-INV-15)."""

from datetime import date
from decimal import Decimal as D

from inventory.domain.alertas import bajo_minimo
from inventory.domain.lotes import dias_restantes, por_vencer

HOY = date(2026, 11, 1)


def test_por_vencer_incluye_hoy_y_el_ultimo_dia_de_la_ventana():
    assert por_vencer(HOY, 30, HOY)
    assert por_vencer(date(2026, 12, 1), 30, HOY)
    assert not por_vencer(date(2026, 12, 2), 30, HOY)
    assert not por_vencer(date(2026, 10, 31), 30, HOY)  # ya vencido: va como "Vencido"
    assert not por_vencer(None, 30, HOY)
    assert dias_restantes(date(2026, 12, 15), HOY) == 44


def test_stock_bajo_solo_con_minimo_y_hasta_igualarlo():
    assert bajo_minimo(D("320"), D("500"))
    assert bajo_minimo(D("500"), D("500"))
    assert not bajo_minimo(D("501"), D("500"))
    assert not bajo_minimo(D("0"), D("0"))  # sin stock mínimo no alerta
