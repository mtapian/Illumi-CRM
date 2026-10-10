"""Tokens de API para integraciones (UC-TEN-11; RF-TEN-43, 45 a 47, 54).

Cada token pertenece a un usuario técnico de la empresa: sus roles definen qué puede
leer. El usuario técnico se crea y se gestiona solo desde aquí.
"""

from collections.abc import Callable
from datetime import date

from shared.application.autorizacion import Actor
from shared.domain.errores import NoEncontrado
from tenancy.application.usuarios import _BaseUsuarios
from tenancy.domain.errores import EmpresaNoOperativa, SinApiIntegracion
from tenancy.domain.tokens import API, hash_token, nuevo_token, prefijo_token

GESTIONAR = "api.token.gestionar"
SIN_API = "Tu plan no incluye la API de integración"


class _BaseTokens(_BaseUsuarios):
    permiso_requerido = GESTIONAR

    def __init__(self, repo, habilitaciones, atomic, empresa_activa: Callable[[int, date], bool]):
        super().__init__(repo, habilitaciones, atomic)
        self._empresa_activa = empresa_activa


class CrearTokenApi(_BaseTokens):
    def ejecutar(self, actor: Actor, nombre: str, tecnico: str, rol_ids, hoy: date) -> str:
        """Devuelve el token en claro: es la única vez que sale del sistema (RF-TEN-45)."""
        if API not in self._habilitaciones(actor.empresa_id, hoy):
            raise SinApiIntegracion(SIN_API)
        if not self._empresa_activa(actor.empresa_id, hoy):
            raise EmpresaNoOperativa("La empresa no puede operar: no se crean tokens")
        with self._atomic():
            tecnico_id = self._repo.usuario_tecnico(actor.empresa_id, tecnico)
            if tecnico_id is None:
                _, roles = self._roles_validados(actor, rol_ids, hoy)
                tecnico_id = self._repo.crear_usuario_tecnico(actor.empresa_id, tecnico)
                self._repo.asignar_roles(tecnico_id, list(rol_ids))
                self._auditar(
                    actor, "USUARIO_ROL", tecnico_id, "ASIGNAR", {"roles": []}, {"roles": roles}
                )
            token = nuevo_token()
            token_id = self._repo.guardar_token(
                actor.empresa_id,
                tecnico_id,
                nombre,
                hash_token(token),
                prefijo_token(token),
                actor.usuario_id,
            )
            despues = {"nombre": nombre, "prefijo": prefijo_token(token), "tecnico": tecnico}
            self._auditar(actor, "TOKEN_API", token_id, "CREAR", None, despues)
            return token


class RevocarTokenApi(_BaseTokens):
    """El token deja de funcionar desde la siguiente llamada (RF-TEN-47)."""

    def ejecutar(self, actor: Actor, token_id: int) -> None:
        with self._atomic():
            nombre, revocado = self._repo.token(actor.empresa_id, token_id)
            if revocado:
                return
            self._repo.revocar_token(token_id)
            self._auditar(
                actor,
                "TOKEN_API",
                token_id,
                "REVOCAR",
                {"nombre": nombre, "revocado": False},
                {"nombre": nombre, "revocado": True},
            )


class DesactivarUsuarioTecnico(_BaseTokens):
    """Desactiva el usuario técnico y revoca todos sus tokens (RF-TEN-54)."""

    def ejecutar(self, actor: Actor, usuario_id: int) -> None:
        with self._atomic():
            activo, es_tecnico = self._repo.usuario(actor.empresa_id, usuario_id)
            if not es_tecnico:
                raise NoEncontrado("No encontrado")
            self._repo.actualizar_usuario(usuario_id, is_active=False)
            self._repo.revocar_tokens_de(usuario_id)
            self._auditar(
                actor, "USUARIO", usuario_id, "DESACTIVAR", {"activo": activo}, {"activo": False}
            )
