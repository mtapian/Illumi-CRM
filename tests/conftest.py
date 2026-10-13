from datetime import date
from decimal import Decimal

import pytest

from catalog.application.puertos import puertos
from purchasing.application.puertos import puertos as puertos_compras
from tenancy.infrastructure.contenedor import sembrador_roles
from tenancy.infrastructure.models import Empresa, Plan, Rol, UsuarioRol
from tenancy.infrastructure.repositorios import (
    sembrar_parametros_plataforma,
    sembrar_tipos_documento,
)


@pytest.fixture
def crear_empresa(db):
    """Crea una empresa con su propio plan (para tests de integración)."""

    def _crear(ruc="20601234565", razon_social="Cervecería Andina S.A.C.", **kw):
        sembrar_tipos_documento()  # los tests con transacciones reales vacían el maestro
        sembrar_parametros_plataforma()
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


class InventarioFalso:
    """Reemplaza al inventario (épica 0003) en los tests."""

    def __init__(self):
        self.stocks, self.con_movimientos = {}, set()

    def stock(self, producto_id):
        return self.stocks.get(producto_id, Decimal("0"))

    def tiene_movimientos(self, producto_id):
        return producto_id in self.con_movimientos or self.stock(producto_id) > 0


@pytest.fixture
def inventario(monkeypatch):
    falso = InventarioFalso()
    monkeypatch.setattr(puertos, "inventario", falso)
    return falso


class ComprasFalsas:
    """Reemplaza a las compras (0004a) en los tests."""

    def __init__(self):
        self.con_compras = set()

    def tiene_compras(self, proveedor_id):
        return proveedor_id in self.con_compras


@pytest.fixture
def compras(monkeypatch):
    falso = ComprasFalsas()
    monkeypatch.setattr(puertos_compras, "compras", falso)
    return falso
