"""Puertos del shared kernel (plan 0000 §3)."""

from typing import Protocol


class SequencePort(Protocol):
    def siguiente(self, documento: str, serie: str = "") -> int:
        """Siguiente correlativo de la empresa actual; sin huecos ni duplicados."""
        ...
