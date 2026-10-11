"""Desglose informativo del precio de lista, que ya incluye IGV e ISC (RF-CAT-30).

Cada venta calcula sus impuestos a su fecha (épica 0006); esto solo se muestra en la ficha.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True)
class Desglose:
    valor: Decimal
    isc: Decimal
    igv: Decimal


def desglose_precio(precio: Decimal, igv_pct: Decimal, isc_unitario: Decimal) -> Desglose:
    """Base del IGV = precio / (1 + IGV); IGV = precio − base; valor = base − ISC."""
    base = (precio / (1 + igv_pct / 100)).quantize(DOS_DECIMALES, ROUND_HALF_UP)
    isc = isc_unitario.quantize(DOS_DECIMALES, ROUND_HALF_UP)
    return Desglose(base - isc, isc, precio - base)
