"""Lo que compras necesita de otros contextos (plan 0002d §1).

Las compras (0004a) reemplazan `puertos.compras`; mientras no existan, ningún proveedor tiene
compras.
"""

from dataclasses import dataclass, field
from typing import Protocol


class ComprasPort(Protocol):
    def tiene_compras(self, proveedor_id: int) -> bool: ...


class SinCompras:
    def tiene_compras(self, proveedor_id: int) -> bool:
        return False


@dataclass
class Puertos:
    compras: ComprasPort = field(default_factory=SinCompras)


puertos = Puertos()
