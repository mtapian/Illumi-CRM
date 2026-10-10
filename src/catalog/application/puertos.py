"""Lo que el catálogo necesita de otros contextos (plan 0002a §1).

Inventario (0003) reemplaza `puertos.inventario`; recetas (0005) y pedidos (0006) agregan
sus contadores a `puertos.referencias`. Mientras no existan, no hay stock ni referencias.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


class InventarioConsultaPort(Protocol):
    def stock(self, producto_id: int) -> Decimal: ...
    def tiene_movimientos(self, producto_id: int) -> bool: ...


class SinInventario:
    """Antes de la épica 0003 ningún producto tiene stock ni movimientos."""

    def stock(self, producto_id: int) -> Decimal:
        return Decimal("0")

    def tiene_movimientos(self, producto_id: int) -> bool:
        return False


@dataclass
class Puertos:
    inventario: InventarioConsultaPort = field(default_factory=SinInventario)
    referencias: list[Callable[[int], int]] = field(default_factory=list)  # producto → usos

    def referencias_externas(self, producto_id: int) -> int:
        return sum(contar(producto_id) for contar in self.referencias)


puertos = Puertos()
