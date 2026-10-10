"""Datos iniciales de una empresa nueva (RF-TEN-01; plan 0001a §4).

Tenancy no conoce a los demás contextos: cada uno registra su sembrador desde su
`AppConfig.ready()` con `sembradores.registrar(...)`.
"""

from collections.abc import Callable
from datetime import date

SembradorInicial = Callable[[int, int, date], None]  # (empresa_id, admin_id, hoy)


class RegistroSembradores:
    def __init__(self):
        self._sembradores: list[SembradorInicial] = []

    def registrar(self, sembrador: SembradorInicial) -> None:
        if sembrador not in self._sembradores:
            self._sembradores.append(sembrador)

    def sembrar(self, empresa_id: int, admin_id: int, hoy: date) -> None:
        for sembrador in self._sembradores:
            sembrador(empresa_id, admin_id, hoy)


sembradores = RegistroSembradores()
