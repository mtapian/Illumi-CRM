"""Qué lote sale cuando no se indica: FEFO (primero vence, primero sale) o FIFO (primero
entra, primero sale), según el producto (spec 0003a, RF-INV-22; 0002a enmienda 6)."""

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


def orden_fifo(e: Existencia) -> tuple:
    """El lote de ingreso más antiguo primero, sin mirar el vencimiento; sin lote, al último."""
    return (e.lote is None, e.ingreso or date.max, e.id_)


ORDEN = {"FEFO": orden_fefo, "FIFO": orden_fifo}


def asignar_fefo(
    existencias: list[Existencia], cant: Decimal, hoy: date, unidad: str, estrategia="FEFO"
) -> list[tuple[Existencia, Decimal]]:
    """Reparte `cant` entre las existencias no vencidas en el orden de la estrategia."""
    usables = sorted(
        (e for e in existencias if e.cantidad > 0 and not lote_vencido(e.vencimiento, hoy)),
        key=ORDEN[estrategia],
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
