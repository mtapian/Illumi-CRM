"""RF-TEN-05, 18, 19, 20: estado de la suscripción calculado con `hoy` (hora de Lima)."""

from datetime import date, timedelta

import pytest

from tenancy.domain.suscripcion import (
    Estado,
    dias_para_vencer,
    estado_suscripcion,
    fecha_termino_prueba,
    mostrar_aviso_vencimiento,
)

TERMINO = date(2026, 10, 24)


def test_la_fecha_de_termino_es_inclusiva():
    assert estado_suscripcion(Estado.TRIAL, TERMINO, TERMINO) == Estado.TRIAL
    assert estado_suscripcion(Estado.ACTIVA, TERMINO, TERMINO) == Estado.ACTIVA


def test_vence_al_dia_siguiente():
    assert estado_suscripcion(Estado.TRIAL, TERMINO, TERMINO + timedelta(days=1)) == Estado.VENCIDA
    assert estado_suscripcion(Estado.ACTIVA, TERMINO, TERMINO + timedelta(days=1)) == Estado.VENCIDA


def test_suspendida_prevalece_sobre_la_fecha():
    assert estado_suscripcion(Estado.SUSPENDIDA, TERMINO, TERMINO) == Estado.SUSPENDIDA
    assert estado_suscripcion(Estado.SUSPENDIDA, None, TERMINO) == Estado.SUSPENDIDA


def test_sin_fecha_de_termino_no_vence():
    assert estado_suscripcion(Estado.ACTIVA, None, date(2099, 1, 1)) == Estado.ACTIVA


@pytest.mark.parametrize(
    ("dias", "aviso"), [(8, False), (7, True), (5, True), (0, True), (-1, False)]
)
def test_aviso_a_7_dias_o_menos(dias, aviso):
    hoy = TERMINO - timedelta(days=dias)
    assert dias_para_vencer(TERMINO, hoy) == dias
    assert mostrar_aviso_vencimiento(TERMINO, hoy) is aviso


def test_sin_fecha_no_hay_aviso():
    assert dias_para_vencer(None, TERMINO) is None
    assert mostrar_aviso_vencimiento(None, TERMINO) is False


def test_fecha_de_termino_de_la_prueba():
    assert fecha_termino_prueba(date(2026, 10, 10), 14) == date(2026, 10, 24)
