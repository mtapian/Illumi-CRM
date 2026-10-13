"""Desglose de un precio que ya incluye sus impuestos (RF-CAT-30, 59): `desglose_linea`."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Desglose:
    valor: Decimal
    isc: Decimal
    igv: Decimal
