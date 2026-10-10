"""Roles propios de la empresa (UC-TEN-09; RF-TEN-35 a 39, 53). Cada cambio se audita
con el valor anterior y el nuevo (RF-TEN-43).

Un rol solo guarda permisos habilitados (RN-TEN-11), pero conserva los que dejaron de
estarlo: no son efectivos y vuelven a serlo si la plataforma los rehabilita (RF-TEN-39).
"""

from collections.abc import Callable
from datetime import date

from shared.application.autorizacion import Actor, CasoDeUso
from tenancy.application.puertos import AccesosRepo
from tenancy.domain.errores import RolConUsuarios, RolDeSistema
from tenancy.domain.permisos import permisos_habilitados, validar_escalada, validar_permisos_rol

GESTIONAR = "core.rol.gestionar"
NO_EDITABLE = "El rol Administrador no se puede editar ni eliminar"


def _datos(nombre: str, permisos) -> dict:
    return {"nombre": nombre, "permisos": sorted(permisos)}


class _BaseRoles(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: AccesosRepo, habilitaciones: Callable[[int, date], frozenset], atomic):
        self._repo = repo
        self._habilitaciones = habilitaciones
        self._atomic = atomic

    def _validar(self, actor: Actor, permisos, hoy: date) -> frozenset[str]:
        habilitadas = self._habilitaciones(actor.empresa_id, hoy)
        validar_permisos_rol(permisos, habilitadas)
        validar_escalada(actor.permisos, actor.es_admin, permisos, da_rol_admin=False)
        return permisos_habilitados(habilitadas)

    def _auditar(self, actor: Actor, rol_id: int, accion: str, antes, despues) -> None:
        self._repo.auditar(
            actor.empresa_id, actor.usuario_id, "ROL", rol_id, accion, antes, despues
        )

    def _editable(self, actor: Actor, rol_id: int):
        rol = self._repo.rol(actor.empresa_id, rol_id)
        if rol.es_sistema:
            raise RolDeSistema(NO_EDITABLE)
        return rol


class CrearRol(_BaseRoles):
    def ejecutar(self, actor: Actor, nombre: str, permisos, hoy: date) -> int:
        self._validar(actor, permisos, hoy)
        rol_id = self._repo.crear_rol(actor.empresa_id, nombre, set(permisos))
        self._auditar(actor, rol_id, "CREAR", None, _datos(nombre, permisos))
        return rol_id


class EditarRol(_BaseRoles):
    def ejecutar(self, actor: Actor, rol_id: int, nombre: str, permisos, hoy: date) -> None:
        rol = self._editable(actor, rol_id)
        habilitados = self._validar(actor, permisos, hoy)
        guardados = self._repo.permisos_guardados(rol_id)
        nuevos = set(permisos) | (guardados - habilitados)  # conserva lo no habilitado (RF-TEN-39)
        self._repo.actualizar_rol(rol_id, nombre, nuevos)
        self._auditar(
            actor, rol_id, "EDITAR", _datos(rol.nombre, guardados), _datos(nombre, nuevos)
        )


class DuplicarRol(_BaseRoles):
    def ejecutar(self, actor: Actor, rol_id: int, nombre: str, hoy: date) -> int:
        rol = self._editable(actor, rol_id)
        habilitados = self._habilitaciones(actor.empresa_id, hoy)
        validar_escalada(
            actor.permisos, actor.es_admin, rol.permisos & permisos_habilitados(habilitados), False
        )
        nuevo = self._repo.crear_rol(actor.empresa_id, nombre, rol.permisos)
        self._auditar(actor, nuevo, "CREAR", None, _datos(nombre, rol.permisos))
        return nuevo


class CambiarEstadoRol(_BaseRoles):
    """Desactivar un rol quita sus permisos a sus usuarios desde su siguiente acción."""

    def ejecutar(self, actor: Actor, rol_id: int, activo: bool) -> None:
        rol = self._editable(actor, rol_id)
        self._repo.cambiar_estado_rol(rol_id, activo)
        accion = "ACTIVAR" if activo else "DESACTIVAR"
        self._auditar(actor, rol_id, accion, {"activo": rol.activo}, {"activo": activo})


class EliminarRol(_BaseRoles):
    def ejecutar(self, actor: Actor, rol_id: int) -> None:
        with self._atomic():
            rol = self._editable(actor, rol_id)
            if n := self._repo.usuarios_con_rol(rol_id):
                raise RolConUsuarios(f"El rol tiene {n} usuarios; puedes desactivarlo")
            self._repo.eliminar_rol(rol_id)
            self._auditar(actor, rol_id, "ELIMINAR", _datos(rol.nombre, rol.permisos), None)
