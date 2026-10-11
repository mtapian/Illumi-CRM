"""Sembrador de 0001a: rol de sistema "Administrador" y plantillas recortadas a lo
habilitado; el primer usuario queda como Administrador (RF-TEN-01; spec 0001c)."""

from collections.abc import Callable
from datetime import date

from tenancy.application.puertos import RolesRepo
from tenancy.domain.permisos import ADMINISTRADOR
from tenancy.domain.plantillas import roles_iniciales


class SembradorRoles:
    def __init__(self, roles: RolesRepo, habilitaciones: Callable[[int, date], frozenset]):
        self._roles = roles
        self._habilitaciones = habilitaciones

    def __call__(self, empresa_id: int, admin_id: int, hoy: date) -> None:
        admin = self._roles.crear_rol(empresa_id, ADMINISTRADOR, set(), es_sistema=True)
        for nombre, permisos in roles_iniciales(self._habilitaciones(empresa_id, hoy)).items():
            self._roles.crear_rol(empresa_id, nombre, permisos)
        self._roles.asignar_roles(admin_id, [admin])
