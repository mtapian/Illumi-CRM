"""Faltantes de stock en un mensaje (0005a RF-PRD-09; 0006a RF-VEN-08): lo usan la OP y el
pedido, que validan todo antes de mover stock o cambiar de estado."""

from decimal import ROUND_HALF_UP, Decimal

CUATRO = Decimal("0.0001")


def faltantes(requeridos: dict[str, Decimal], disponibles: dict[str, Decimal]) -> str | None:
    """Todos los faltantes en un mensaje, o None si alcanza. Claves: el SKU (o SKU y lote)."""
    partes = [
        f"{sku} faltan {(q - disponibles.get(sku, Decimal('0'))).quantize(CUATRO, ROUND_HALF_UP)}"
        for sku, q in requeridos.items()
        if q > disponibles.get(sku, Decimal("0"))
    ]
    return f"Stock insuficiente: {'; '.join(partes)}" if partes else None
