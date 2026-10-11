"""Alertas del inventario (spec 0003c; RF-INV-14)."""

from decimal import Decimal


def bajo_minimo(stock_total: Decimal, minimo: Decimal) -> bool:
    """Stock bajo: solo con stock mínimo > 0, y hasta igualarlo."""
    return minimo > 0 and stock_total <= minimo
