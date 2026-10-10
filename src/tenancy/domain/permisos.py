"""Permisos efectivos de un usuario y reglas de roles (spec 0001c; RN-TEN-04, 05, 10, 11).

Permisos efectivos = (∪ permisos de sus roles activos) ∩ (permisos habilitados).
El rol de sistema "Administrador" equivale a todos los permisos habilitados.
"""

from dataclasses import dataclass

from shared.domain.accesos import CATALOGO, MODULOS, PERMISOS
from tenancy.domain.errores import EscaladaDePrivilegios, PermisoNoHabilitado

ADMINISTRADOR = "Administrador"
NO_DISPONIBLE = "No disponible en tu plan"


@dataclass(frozen=True)
class Rol:
    nombre: str
    permisos: frozenset[str]
    es_sistema: bool = False
    activo: bool = True


def permisos_habilitados(habilitadas) -> frozenset[str]:
    return frozenset(p for p, f in PERMISOS.items() if f in habilitadas)


def permisos_de_roles(roles) -> frozenset[str]:
    """Lo que dan los roles activos, esté o no habilitado."""
    activos = [r for r in roles if r.activo]
    if any(r.es_sistema for r in activos):
        return frozenset(PERMISOS)
    return frozenset().union(*(r.permisos for r in activos))


def permisos_efectivos(roles, habilitadas) -> frozenset[str]:
    return permisos_de_roles(roles) & permisos_habilitados(habilitadas)


def origen_permisos(roles, habilitadas) -> dict[str, list[str] | str]:
    """Para la ficha del usuario: permiso → roles que lo dan, o "No disponible en tu plan"."""
    habilitados = permisos_habilitados(habilitadas)
    origen: dict[str, list[str] | str] = {}
    for rol in (r for r in roles if r.activo):
        for p in permisos_de_roles([rol]):
            if p not in habilitados:
                origen[p] = NO_DISPONIBLE
            elif not rol.es_sistema or p not in origen:
                origen.setdefault(p, []).append(rol.nombre)
    return origen


def agrupar_por_modulo(permisos) -> dict[str, list[str]]:
    """{nombre del módulo: [permisos]} en el orden del catálogo."""
    permisos = set(permisos)
    grupos: dict[str, list[str]] = {}
    for f in CATALOGO.values():
        for p in f.permisos:
            if p in permisos:
                grupos.setdefault(MODULOS[f.modulo], []).append(p)
    return grupos


def validar_permisos_rol(permisos, habilitadas) -> None:
    """RN-TEN-11: un rol solo guarda permisos de funcionalidades habilitadas."""
    for p in sorted(set(permisos) - permisos_habilitados(habilitadas)):
        raise PermisoNoHabilitado(f"El permiso {p} no está incluido en tu plan")


def validar_escalada(permisos_actor, es_admin_actor, permisos_a_dar, da_rol_admin) -> None:
    """RF-TEN-53: nadie da un permiso o el rol Administrador que él mismo no tiene."""
    if es_admin_actor:
        return
    if da_rol_admin:
        raise EscaladaDePrivilegios("Solo un administrador puede asignar el rol Administrador")
    if set(permisos_a_dar) - set(permisos_actor):
        raise EscaladaDePrivilegios("No puedes dar permisos que no tienes")


def cabe_en_limite(activos_no_tecnicos: int, limite: int | None) -> bool:
    return limite is None or activos_no_tecnicos < limite


def quedan_administradores(administradores_activos_despues: int) -> bool:
    return administradores_activos_despues > 0
