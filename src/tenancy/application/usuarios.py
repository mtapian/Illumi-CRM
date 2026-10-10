"""Gestión de usuarios de la empresa (UC-TEN-03; RF-TEN-10 a 13, 53).

Los usuarios nunca se borran: se desactivan y conservan su autoría (RF-TEN-13).
Los cambios que pueden dejar a la empresa sin administrador bloquean la fila de la
empresa, así dos administradores no se desactivan entre sí a la vez (RF-TEN-12).
"""

from collections.abc import Callable
from datetime import date

from shared.application.autorizacion import Actor, CasoDeUso
from tenancy.application.puertos import AccesosRepo
from tenancy.domain.errores import EmailDuplicado, LimiteUsuariosPlan, UltimoAdministrador
from tenancy.domain.permisos import (
    cabe_en_limite,
    permisos_efectivos,
    quedan_administradores,
    validar_escalada,
)

GESTIONAR = "core.usuario.gestionar"
Habilitaciones = Callable[[int, date], frozenset[str]]


class _BaseUsuarios(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: AccesosRepo, habilitaciones: Habilitaciones, atomic: Callable):
        self._repo = repo
        self._habilitaciones = habilitaciones
        self._atomic = atomic

    def _validar_roles(self, actor: Actor, rol_ids, hoy: date) -> bool:
        """Controla la escalada; devuelve si entre los roles está el de Administrador."""
        return self._roles_validados(actor, rol_ids, hoy)[0]

    def _roles_validados(self, actor: Actor, rol_ids, hoy: date):
        roles = self._repo.roles(actor.empresa_id, rol_ids)
        da_admin = any(r.es_sistema for r in roles)
        permisos = permisos_efectivos(
            [r for r in roles if not r.es_sistema], self._habilitaciones(actor.empresa_id, hoy)
        )
        validar_escalada(actor.permisos, actor.es_admin, permisos, da_admin)
        return da_admin, sorted(r.nombre for r in roles)

    def _auditar(self, actor: Actor, entidad: str, usuario_id: int, accion, antes, despues):
        """RF-TEN-43: quién, cuándo, valor anterior y nuevo."""
        self._repo.auditar(
            actor.empresa_id, actor.usuario_id, entidad, usuario_id, accion, antes, despues
        )

    def _exigir_limite(self, empresa_id: int) -> None:
        limite = self._repo.bloquear_empresa(empresa_id)
        if not cabe_en_limite(self._repo.contar_activos_no_tecnicos(empresa_id), limite):
            raise LimiteUsuariosPlan(f"Tu plan permite hasta {limite} usuarios activos")

    @staticmethod
    def _exigir_administrador(administradores_despues: set[int]) -> None:
        if not quedan_administradores(len(administradores_despues)):
            raise UltimoAdministrador("La empresa debe tener al menos un administrador activo")


class CrearUsuario(_BaseUsuarios):
    def ejecutar(self, actor: Actor, nombre, email, password, rol_ids, hoy: date) -> int:
        with self._atomic():
            self._exigir_limite(actor.empresa_id)
            if self._repo.existe_email(email):
                raise EmailDuplicado("Ya existe un usuario con ese email")
            _, nombres = self._roles_validados(actor, rol_ids, hoy)
            usuario_id = self._repo.crear_usuario(actor.empresa_id, nombre, email, password)
            self._repo.asignar_roles(usuario_id, list(rol_ids))
            self._auditar(
                actor, "USUARIO_ROL", usuario_id, "ASIGNAR", {"roles": []}, {"roles": nombres}
            )
            return usuario_id


class EditarUsuario(_BaseUsuarios):
    def ejecutar(self, actor: Actor, usuario_id: int, nombre: str) -> None:
        self._repo.usuario(actor.empresa_id, usuario_id)
        self._repo.actualizar_usuario(usuario_id, nombre=nombre)


class AsignarRoles(_BaseUsuarios):
    def ejecutar(self, actor: Actor, usuario_id: int, rol_ids, hoy: date) -> None:
        with self._atomic():
            self._repo.bloquear_empresa(actor.empresa_id)
            activo, _ = self._repo.usuario(actor.empresa_id, usuario_id)
            da_admin, nombres = self._roles_validados(actor, rol_ids, hoy)
            admins = self._repo.administradores_activos(actor.empresa_id) - {usuario_id}
            self._exigir_administrador(admins | ({usuario_id} if da_admin and activo else set()))
            antes = self._repo.nombres_roles(usuario_id)
            self._repo.asignar_roles(usuario_id, list(rol_ids))
            self._auditar(
                actor, "USUARIO_ROL", usuario_id, "ASIGNAR", {"roles": antes}, {"roles": nombres}
            )


class CambiarEstadoUsuario(_BaseUsuarios):
    def ejecutar(self, actor: Actor, usuario_id: int, activo: bool) -> None:
        with self._atomic():
            self._repo.bloquear_empresa(actor.empresa_id)
            estaba_activo, es_tecnico = self._repo.usuario(actor.empresa_id, usuario_id)
            if activo and not estaba_activo and not es_tecnico:
                self._exigir_limite(actor.empresa_id)
            if not activo:
                self._exigir_administrador(
                    self._repo.administradores_activos(actor.empresa_id) - {usuario_id}
                )
            self._repo.actualizar_usuario(usuario_id, is_active=activo)
            if not activo and es_tecnico:
                self._repo.revocar_tokens_de(usuario_id)  # RF-TEN-54
            accion = "ACTIVAR" if activo else "DESACTIVAR"
            self._auditar(
                actor, "USUARIO", usuario_id, accion, {"activo": estaba_activo}, {"activo": activo}
            )
