"""Existencias por producto × almacén × lote y movimientos (spec 0003a; RF-INV-17, 19)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from inventory.domain.costo import cantidad as redondear
from inventory.domain.errores import StockInsuficiente

ENTRADA, SALIDA = "ENTRADA", "SALIDA"


@dataclass(frozen=True)
class Existencia:
    """Stock de un producto en un almacén y lote; `lote=None` es el stock sin lote.
    `producto` y `almacen` son los nombres para los mensajes."""

    cantidad: Decimal
    lote: str | None = None
    vencimiento: date | None = None
    ingreso: date | None = None
    id_: int = 0
    producto: str = ""
    almacen: str = ""


@dataclass(frozen=True)
class Movimiento:
    id: int | None
    tipo: str  # ENTRADA o SALIDA
    cantidad: Decimal
    costo_unitario: Decimal
    almacen_id: int
    lote_id: int | None = None
    revierte_id: int | None = None


def salir(e: Existencia, cant: Decimal) -> Existencia:
    """RF-INV-19 (RN-INV-02): el stock del almacén y lote nunca queda negativo."""
    nueva = redondear(e.cantidad - cant)
    if nueva < 0:
        raise StockInsuficiente(
            f"Stock insuficiente de {e.producto} en {e.almacen}: "
            f"disponible {redondear(e.cantidad)}, requerido {redondear(cant)}"
        )
    return Existencia(nueva, e.lote, e.vencimiento, e.ingreso, e.id_, e.producto, e.almacen)
