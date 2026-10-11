"""Porcentaje de IGV de la empresa (RF-TEN-16)."""

from decimal import Decimal

from tenancy.domain.errores import IgvInvalido


def validar_igv(pct: Decimal) -> Decimal:
    if not Decimal(0) <= pct <= Decimal(100) or pct.as_tuple().exponent < -2:
        raise IgvInvalido("El IGV debe estar entre 0 y 100, con hasta 2 decimales")
    return pct
