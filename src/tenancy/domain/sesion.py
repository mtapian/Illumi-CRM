"""Bloqueo temporal por intentos fallidos (RF-TEN-08; valores de PRD Q6)."""

from datetime import datetime, timedelta

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


def bloqueo_por_intentos(intentos_fallidos: int, ahora: datetime) -> datetime | None:
    """Devuelve hasta cuándo queda bloqueado el usuario, o None si no se bloquea."""
    if intentos_fallidos >= MAX_INTENTOS:
        return ahora + timedelta(minutes=MINUTOS_BLOQUEO)
    return None


def esta_bloqueado(bloqueado_hasta: datetime | None, ahora: datetime) -> bool:
    return bloqueado_hasta is not None and ahora < bloqueado_hasta
