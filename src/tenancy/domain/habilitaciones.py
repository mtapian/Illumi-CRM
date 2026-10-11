"""Habilitaciones de una empresa: plan ± ajustes vigentes (spec 0001b).

Se calculan en cada request; no se copian a la empresa. Así un cambio de plan aplica
de inmediato y un ajuste vencido deja de contar sin ningún cron (RF-TEN-27, 30).
"""

from dataclasses import dataclass
from datetime import date

from shared.domain.accesos import CATALOGO, CORE, en_orden, requeridas
from tenancy.domain.errores import CoreNoSeQuita

AGREGAR, QUITAR = "AGREGAR", "QUITAR"


@dataclass(frozen=True)
class Ajuste:
    funcionalidad: str
    tipo: str  # AGREGAR | QUITAR
    vigente_hasta: date | None = None


def ajuste_vigente(ajuste: Ajuste, hoy: date) -> bool:
    """La fecha de fin es inclusiva (RN-TEN-08)."""
    return ajuste.vigente_hasta is None or hoy <= ajuste.vigente_hasta


def habilitaciones_efectivas(funcs_plan, ajustes, hoy: date) -> frozenset[str]:
    vigentes = [a for a in ajustes if ajuste_vigente(a, hoy)]
    agregadas = {a.funcionalidad for a in vigentes if a.tipo == AGREGAR}
    quitadas = {a.funcionalidad for a in vigentes if a.tipo == QUITAR}
    return frozenset((set(funcs_plan) | agregadas) - quitadas) | CORE


def estado_funcionalidad(codigo: str, funcs_plan, ajustes, hoy: date) -> str:
    ajuste = next(
        (a for a in ajustes if a.funcionalidad == codigo and ajuste_vigente(a, hoy)), None
    )
    if codigo in CORE or (codigo in funcs_plan and ajuste is None):
        return "Incluida en el plan"
    if ajuste is not None:
        return "Agregada" if ajuste.tipo == AGREGAR else "Quitada"
    return "No incluida"


def funcionalidades_de_modulo(modulo: str) -> list[str]:
    return [c for c, f in CATALOGO.items() if f.modulo == modulo]


def dependientes_afectados(a_quitar, habilitadas) -> list[str]:
    """Habilitadas que quedarían sin una funcionalidad que requieren (RN-TEN-09)."""
    if set(a_quitar) & CORE:
        raise CoreNoSeQuita("CORE no se puede deshabilitar")
    quedan = set(habilitadas) - set(a_quitar)
    return en_orden(c for c in quedan if requeridas(c) & set(a_quitar))
