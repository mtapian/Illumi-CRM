"""Lo que compras necesita de otros contextos (plan 0002d §1).

Las compras (0004a) llenan `puertos.compras` al arrancar la app (`ComprasOrm`); `SinCompras`
queda para los tests de proveedores.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


class IgvPort(Protocol):
    """El % de IGV vigente de la empresa a una fecha (lo implementa la fachada de tenancy)."""

    def igv_vigente(self, fecha: date) -> Decimal: ...


class ComprasPort(Protocol):
    def tiene_compras(self, proveedor_id: int) -> bool: ...


class SinCompras:
    def tiene_compras(self, proveedor_id: int) -> bool:
        return False


@dataclass
class Puertos:
    compras: ComprasPort = field(default_factory=SinCompras)


puertos = Puertos()
