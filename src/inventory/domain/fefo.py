"""FEFO: primero sale lo que vence antes (spec 0003a; RF-INV-22, RN-INV-05, 06)."""

from datetime import date
from decimal import Decimal

from inventory.domain.costo import cantidad as redondear
from inventory.domain.errores import StockInsuficiente
from inventory.domain.existencia import Existencia
from inventory.domain.lotes import lote_vencido


def orden_fefo(e: Existencia) -> tuple:
    """Vencimiento más cercano; a igual vencimiento, el más antiguo. Los lotes sin fecha van
    al final, del más antiguo al más nuevo, y el stock sin lote, al último."""
    return (
        e.vencimiento is None,
        e.vencimiento or date.max,
        e.lote is None,
        e.ingreso or date.max,
        e.id_,
    )


def asignar_fefo(
    existencias: list[Existencia], cant: Decimal, hoy: date, unidad: str
) -> list[tuple[Existencia, Decimal]]:
    """Reparte `cant` entre las existencias no vencidas en orden FEFO."""
    usables = sorted(
        (e for e in existencias if e.cantidad > 0 and not lote_vencido(e.vencimiento, hoy)),
        key=orden_fefo,
    )
    disponible = sum((e.cantidad for e in usables), Decimal("0"))
    if disponible < cant:
        cifra = f"{redondear(disponible).normalize():f}"
        raise StockInsuficiente(f"Stock disponible insuficiente: {cifra} {unidad} sin vencer")
    asignado, falta = [], cant
    for e in usables:
        if falta <= 0:
            break
        toma = min(e.cantidad, falta)
        asignado.append((e, toma))
        falta -= toma
    return asignado
