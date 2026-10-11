"""Reversión de movimientos por anulación (spec 0003a; RF-INV-20, 21, RN-INV-04)."""

from dataclasses import replace

from inventory.domain.costo import CORREGIR
from inventory.domain.errores import AnulacionConConsumoPosterior
from inventory.domain.existencia import ENTRADA, SALIDA, Movimiento


def hubo_salidas_posteriores(movimientos: list[Movimiento], entrada: Movimiento) -> bool:
    """Cualquier salida del producto, en cualquier almacén o lote, posterior a la entrada. La
    reversión de otra entrada no cuenta: no consume esta."""
    return any(
        m.tipo == SALIDA and m.id > entrada.id and m.revierte_id is None for m in movimientos
    )


def validar_reversion(movimientos: list[Movimiento], a_revertir: list[Movimiento]) -> None:
    """RF-INV-21 (Q12 = A): una entrada ya consumida no se anula; se corrige por ajuste."""
    for m in a_revertir:
        if m.tipo == ENTRADA and hubo_salidas_posteriores(movimientos, m):
            raise AnulacionConConsumoPosterior(CORREGIR)


def inversos_de(movimientos: list[Movimiento]) -> list[Movimiento]:
    """Movimientos opuestos al costo original de cada uno (RF-INV-20)."""
    opuesto = {ENTRADA: SALIDA, SALIDA: ENTRADA}
    return [replace(m, id=None, tipo=opuesto[m.tipo], revierte_id=m.id) for m in movimientos]
