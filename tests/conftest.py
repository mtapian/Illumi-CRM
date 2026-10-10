from datetime import date

import pytest

from tenancy.infrastructure.contenedor import sembrador_roles
from tenancy.infrastructure.models import Empresa, Plan, Rol, UsuarioRol


@pytest.fixture
def crear_empresa(db):
    """Crea una empresa con su propio plan (para tests de integración)."""

    def _crear(ruc="20601234565", razon_social="Cervecería Andina S.A.C.", **kw):
        plan = Plan.objects.create(nombre=f"Plan {ruc}", slug=f"plan-{ruc}")
        return Empresa.objects.create(ruc=ruc, razon_social=razon_social, plan=plan, **kw)

    return _crear


def asignar_rol(usuario, nombre="Administrador"):
    """Siembra los roles iniciales de la empresa si faltan y asigna el rol (0001c)."""
    if not Rol.all_tenants.filter(empresa_id=usuario.empresa_id).exists():
        sembrador_roles()(usuario.empresa_id, usuario.id, date.today())
        UsuarioRol.objects.filter(usuario=usuario).delete()
    rol = Rol.all_tenants.get(empresa_id=usuario.empresa_id, nombre=nombre)
    UsuarioRol.objects.get_or_create(usuario=usuario, rol=rol)
    return usuario
