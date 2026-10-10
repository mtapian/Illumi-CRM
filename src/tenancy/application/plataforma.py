"""Casos de uso del super admin: planes, estado de empresas y habilitaciones (spec 0001b).

Son datos de plataforma: se administran sin elegir una empresa (constitución, art. 3.1).
"""

from collections.abc import Callable
from datetime import date
from typing import Protocol

from shared.domain.accesos import CORE, en_orden, funcionalidad, nombres, requeridas
from tenancy.application.operaciones_en_curso import RegistroContadores
from tenancy.application.puertos import HabilitacionesRepo
from tenancy.domain.errores import (
    DependenciasFaltantes,
    DependientesHabilitados,
    MotivoObligatorio,
)
from tenancy.domain.habilitaciones import (
    AGREGAR,
    QUITAR,
    dependientes_afectados,
    habilitaciones_efectivas,
)
from tenancy.domain.suscripcion import Estado


class PlataformaRepo(HabilitacionesRepo, Protocol):
    def estado(self, empresa_id: int) -> tuple[Estado, str]:
        """(estado, estado_previo)."""
        ...

    def actualizar_empresa(self, empresa_id: int, **campos) -> None: ...
    def registrar_actividad(
        self, empresa_id: int, actor_id: int | None, accion: str, motivo: str, detalle: dict
    ) -> None: ...
    def guardar_ajustes(
        self,
        empresa_id: int,
        funcionalidades: list[str],
        tipo: str,
        hasta: date | None,
        motivo: str,
        actor_id: int | None,
    ) -> None:
        """Reemplaza el ajuste activo de cada funcionalidad por uno nuevo."""
        ...

    def reemplazar_plan(
        self, plan_id: int, funcionalidades: set[str], limites: dict[str, int | None]
    ) -> None: ...
    def empresas_con_plan(self, plan_id: int) -> int: ...


def _iso(fecha: date | None) -> str | None:
    return fecha.isoformat() if fecha else None


def _exigir_motivo(motivo: str) -> str:
    if not (motivo or "").strip():
        raise MotivoObligatorio("El motivo es obligatorio")
    return motivo.strip()


def _validar_dependencias(funcionalidades, disponibles) -> None:
    """RN-TEN-09: cada funcionalidad necesita todas las que requiere."""
    errores = []
    for f in en_orden(funcionalidades):
        faltan = requeridas(f) - set(disponibles) - CORE
        if faltan:
            errores.append(f"{funcionalidad(f).nombre} requiere: {nombres(faltan)}")
    if errores:
        raise DependenciasFaltantes("; ".join(errores))


class Plataforma:
    def __init__(self, repo: PlataformaRepo, contadores: RegistroContadores, atomic: Callable):
        self._repo = repo
        self._contadores = contadores
        self._atomic = atomic

    # --- UC-TEN-06: estado y plan de la empresa (RF-TEN-22, 23) ---

    def activar_plan(self, empresa_id, plan_id, hasta: date | None, motivo, actor_id) -> None:
        motivo = _exigir_motivo(motivo)
        with self._atomic():
            self._repo.actualizar_empresa(
                empresa_id, estado=Estado.ACTIVA, plan_id=plan_id, fecha_termino=hasta
            )
            detalle = {"plan_id": plan_id, "hasta": _iso(hasta)}
            self._repo.registrar_actividad(empresa_id, actor_id, "ACTIVAR_PLAN", motivo, detalle)

    def suspender(self, empresa_id, motivo, actor_id) -> None:
        motivo = _exigir_motivo(motivo)
        with self._atomic():
            estado, _ = self._repo.estado(empresa_id)
            if estado != Estado.SUSPENDIDA:
                self._repo.actualizar_empresa(
                    empresa_id, estado=Estado.SUSPENDIDA, estado_previo=estado
                )
            self._repo.registrar_actividad(empresa_id, actor_id, "SUSPENDER", motivo, {})

    def reactivar(self, empresa_id, motivo, actor_id) -> None:
        """Vuelve al estado anterior a la suspensión; los datos nunca se tocaron (RN-GEN-11)."""
        motivo = _exigir_motivo(motivo)
        with self._atomic():
            estado, previo = self._repo.estado(empresa_id)
            if estado == Estado.SUSPENDIDA:
                self._repo.actualizar_empresa(
                    empresa_id, estado=previo or Estado.ACTIVA, estado_previo=""
                )
            self._repo.registrar_actividad(empresa_id, actor_id, "REACTIVAR", motivo, {})

    def cambiar_plan(self, empresa_id, plan_id, motivo, actor_id) -> None:
        """Las habilitaciones base pasan a ser las del plan nuevo; los ajustes se conservan."""
        motivo = _exigir_motivo(motivo)
        with self._atomic():
            self._repo.actualizar_empresa(empresa_id, plan_id=plan_id)
            self._repo.registrar_actividad(
                empresa_id, actor_id, "CAMBIAR_PLAN", motivo, {"plan_id": plan_id}
            )

    # --- UC-TEN-07: funcionalidades de un plan (RF-TEN-25 a 27) ---

    def configurar_plan(self, plan_id, funcionalidades, limites, confirmado: bool) -> int:
        """Sin confirmar, solo devuelve cuántas empresas se verán afectadas."""
        funcionalidades = set(funcionalidades) - CORE
        _validar_dependencias(funcionalidades, funcionalidades)
        afectadas = self._repo.empresas_con_plan(plan_id)
        if confirmado:
            self._repo.reemplazar_plan(plan_id, funcionalidades, limites)
        return afectadas

    # --- UC-TEN-08: ajustes por empresa (RF-TEN-29 a 34) ---

    def habilitadas(self, empresa_id: int, hoy: date) -> frozenset[str]:
        return habilitaciones_efectivas(
            self._repo.funcionalidades_plan(empresa_id), self._repo.ajustes(empresa_id), hoy
        )

    def agregar(self, empresa_id, funcionalidades, motivo, hasta, actor_id, hoy) -> None:
        motivo = _exigir_motivo(motivo)
        with self._atomic():
            _validar_dependencias(
                funcionalidades, self.habilitadas(empresa_id, hoy) | set(funcionalidades)
            )
            self._guardar(empresa_id, funcionalidades, AGREGAR, hasta, motivo, actor_id)

    def quitar(
        self, empresa_id, funcionalidades, motivo, hasta, actor_id, hoy, confirmado: bool
    ) -> list[str]:
        """Devuelve las advertencias de operaciones en curso; sin confirmar, no guarda (RF-TEN-32).

        No borra datos ni roles: los permisos solo dejan de ser efectivos (RF-TEN-33).
        """
        motivo = _exigir_motivo(motivo)
        with self._atomic():
            afectadas = dependientes_afectados(funcionalidades, self.habilitadas(empresa_id, hoy))
            if afectadas:
                raise DependientesHabilitados(
                    f"No se puede quitar {nombres(funcionalidades)}: "
                    f"la requieren {nombres(afectadas)}"
                )
            advertencias = self._contadores.advertencias(empresa_id, funcionalidades)
            if confirmado or not advertencias:
                self._guardar(empresa_id, funcionalidades, QUITAR, hasta, motivo, actor_id)
                return []
            return advertencias

    def _guardar(self, empresa_id, funcionalidades, tipo, hasta, motivo, actor_id) -> None:
        funcionalidades = en_orden(funcionalidades)
        self._repo.guardar_ajustes(empresa_id, funcionalidades, tipo, hasta, motivo, actor_id)
        detalle = {
            "funcionalidades": funcionalidades,
            "hasta": hasta.isoformat() if hasta else None,
        }
        self._repo.registrar_actividad(empresa_id, actor_id, tipo, motivo, detalle)
