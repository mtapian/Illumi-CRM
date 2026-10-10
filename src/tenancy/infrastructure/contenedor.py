"""Arma los casos de uso de tenancy con sus adaptadores reales."""

from datetime import date

from django.db import transaction

from shared.application.autorizacion import Actor
from tenancy.application.empresa import ActualizarEmpresa, CambiarIgv
from tenancy.application.fachada import TenancyService
from tenancy.application.operaciones_en_curso import contadores
from tenancy.application.plataforma import Plataforma
from tenancy.application.registro import RegistrarEmpresa
from tenancy.application.sembrador_roles import SembradorRoles
from tenancy.application.sembradores import RegistroSembradores, sembradores
from tenancy.domain.permisos import permisos_de_roles, permisos_efectivos
from tenancy.infrastructure.repositorios import (
    AccesosOrm,
    EmpresasOrm,
    HabilitacionesOrm,
    ParametrosOrm,
    PlataformaOrm,
    RegistroOrm,
    RolesOrm,
    roles_de_usuario,
)


def tenancy_service() -> TenancyService:
    return TenancyService(ParametrosOrm(), EmpresasOrm(), HabilitacionesOrm())


def registrar_empresa(registro: RegistroSembradores | None = None) -> RegistrarEmpresa:
    return RegistrarEmpresa(RegistroOrm(), registro or sembradores, transaction.atomic)


def actualizar_empresa() -> ActualizarEmpresa:
    return ActualizarEmpresa(EmpresasOrm())


def cambiar_igv() -> CambiarIgv:
    return CambiarIgv(ParametrosOrm())


def plataforma() -> Plataforma:
    return Plataforma(PlataformaOrm(), contadores, transaction.atomic)


def sembrador_roles() -> SembradorRoles:
    return SembradorRoles(RolesOrm(), lambda e, hoy: tenancy_service().habilitaciones_de(e, hoy))


def _habilitaciones(empresa_id: int, hoy: date) -> frozenset[str]:
    return tenancy_service().habilitaciones_de(empresa_id, hoy)


def actor_de(usuario, hoy: date) -> Actor:
    """Permisos efectivos recalculados en cada request (RF-TEN-40, 42; plan 0001c §4)."""
    roles_usuario = roles_de_usuario(usuario.id)
    return Actor(
        usuario_id=usuario.id,
        empresa_id=usuario.empresa_id,
        permisos=permisos_efectivos(roles_usuario, _habilitaciones(usuario.empresa_id, hoy)),
        permisos_rol=permisos_de_roles(roles_usuario),
        es_admin=any(r.es_sistema and r.activo for r in roles_usuario),
    )


def caso_de_uso(clase):
    """Arma un caso de uso de usuarios o roles: `caso_de_uso(usuarios.CrearUsuario)`."""
    return clase(AccesosOrm(), _habilitaciones, transaction.atomic)


def caso_de_tokens(clase):
    """Arma un caso de uso de tokens de API: `caso_de_tokens(tokens.CrearTokenApi)`."""
    return clase(
        AccesosOrm(), _habilitaciones, transaction.atomic, tenancy_service().empresa_activa
    )
