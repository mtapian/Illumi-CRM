"""Valores que cambian por norma con fecha de vigencia (constitución art. 5.1)."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal


class SinValorVigente(Exception):
    """No hay ningún valor vigente a esa fecha."""


def valor_vigente(historial: Iterable[tuple[date, Decimal]], fecha: date) -> Decimal:
    """Devuelve el valor con la mayor fecha de vigencia que sea <= `fecha`."""
    vigentes = [(desde, valor) for desde, valor in historial if desde <= fecha]
    if not vigentes:
        raise SinValorVigente(f"No hay un valor vigente al {fecha.isoformat()}")
    return max(vigentes)[1]
