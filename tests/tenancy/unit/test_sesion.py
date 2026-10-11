"""RF-TEN-08: 5 intentos fallidos consecutivos bloquean al usuario 15 minutos (Q6)."""

from datetime import UTC, datetime, timedelta

from tenancy.domain.sesion import bloqueo_por_intentos, esta_bloqueado

AHORA = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)


def test_el_cuarto_fallo_no_bloquea():
    assert bloqueo_por_intentos(4, AHORA) is None


def test_el_quinto_fallo_bloquea_15_minutos():
    assert bloqueo_por_intentos(5, AHORA) == AHORA + timedelta(minutes=15)


def test_el_bloqueo_dura_hasta_el_limite():
    hasta = AHORA + timedelta(minutes=15)
    assert esta_bloqueado(hasta, AHORA + timedelta(minutes=14, seconds=59)) is True
    assert esta_bloqueado(hasta, hasta) is False
    assert esta_bloqueado(None, AHORA) is False
