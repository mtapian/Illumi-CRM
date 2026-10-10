"""Contadores de operaciones en curso por funcionalidad (RF-TEN-32).

Cada contexto registra los suyos (p. ej. producción: OP en proceso), así tenancy no
depende de los demás contextos (plan 0001b §6).
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ContadorOperacionesEnCurso:
    funcionalidad: str
    contar: Callable[[int], int]  # empresa_id -> cantidad
    plantilla: str  # p. ej. "La empresa tiene {n} OP en proceso; quedarán sin poder operarse"


class RegistroContadores:
    def __init__(self):
        self._contadores: list[ContadorOperacionesEnCurso] = []

    def registrar(self, contador: ContadorOperacionesEnCurso) -> None:
        self._contadores.append(contador)

    def advertencias(self, empresa_id: int, funcionalidades) -> list[str]:
        avisos = []
        for c in self._contadores:
            if c.funcionalidad in funcionalidades and (n := c.contar(empresa_id)):
                avisos.append(c.plantilla.format(n=n))
        return avisos


contadores = RegistroContadores()
