"""T1 a T3: permisos efectivos, escalada, límite y último administrador
(RF-TEN-10 a 12, 14, 36, 37, 39, 41, 53; RN-TEN-04, 05, 10, 11)."""

import pytest

from shared.domain.accesos import CORE, PERMISOS
from tenancy.domain.errores import EscaladaDePrivilegios, PermisoNoHabilitado
from tenancy.domain.permisos import (
    NO_DISPONIBLE,
    Rol,
    agrupar_por_modulo,
    cabe_en_limite,
    origen_permisos,
    permisos_efectivos,
    quedan_administradores,
    validar_escalada,
    validar_permisos_rol,
)

HABILITADAS = CORE | {"catalogo.productos", "inventario.stock", "ventas.clientes", "ventas.ventas"}
VENDEDOR = Rol("Vendedor", frozenset({"ventas.venta.registrar", "ventas.venta.ver"}))
INVENTARISTA = Rol(
    "Inventarista", frozenset({"inventario.ajuste.registrar", "inventario.stock.ver"})
)


def test_se_unen_los_permisos_de_los_roles_que_estan_habilitados():
    efectivos = permisos_efectivos([VENDEDOR, INVENTARISTA], HABILITADAS)
    assert efectivos == {"ventas.venta.registrar", "ventas.venta.ver", "inventario.stock.ver"}


def test_un_permiso_de_una_funcionalidad_quitada_sigue_en_el_rol_pero_no_es_efectivo():
    assert "inventario.ajuste.registrar" in INVENTARISTA.permisos
    efectivos = permisos_efectivos([INVENTARISTA], HABILITADAS | {"inventario.ajustes"})
    assert "inventario.ajuste.registrar" in efectivos


def test_el_rol_de_sistema_tiene_todos_los_permisos_habilitados():
    admin = Rol("Administrador", frozenset(), es_sistema=True)
    efectivos = permisos_efectivos([admin], HABILITADAS)
    assert efectivos == {p for p, f in PERMISOS.items() if f in HABILITADAS}


def test_un_rol_inactivo_no_suma_y_sin_roles_no_hay_permisos():
    assert permisos_efectivos([Rol("X", VENDEDOR.permisos, activo=False)], HABILITADAS) == set()
    assert permisos_efectivos([], HABILITADAS) == set()


def test_origen_de_cada_permiso():
    origen = origen_permisos([VENDEDOR, INVENTARISTA], HABILITADAS)
    assert origen["ventas.venta.registrar"] == ["Vendedor"]
    assert origen["inventario.ajuste.registrar"] == NO_DISPONIBLE


def test_validar_permisos_rol_rechaza_lo_no_habilitado():
    validar_permisos_rol({"ventas.venta.ver"}, HABILITADAS)
    with pytest.raises(PermisoNoHabilitado, match="produccion.op.ejecutar no está incluido"):
        validar_permisos_rol({"produccion.op.ejecutar"}, HABILITADAS)


def test_escalada_de_privilegios():
    actor = {"core.usuario.gestionar", "ventas.venta.ver"}
    validar_escalada(actor, False, {"ventas.venta.ver"}, da_rol_admin=False)
    with pytest.raises(EscaladaDePrivilegios, match="No puedes dar permisos que no tienes"):
        validar_escalada(actor, False, {"core.rol.gestionar"}, da_rol_admin=False)
    with pytest.raises(EscaladaDePrivilegios, match="Solo un administrador puede asignar"):
        validar_escalada(actor, False, set(), da_rol_admin=True)
    validar_escalada(actor, True, {"core.rol.gestionar"}, da_rol_admin=True)


def test_limite_de_usuarios_y_ultimo_administrador():
    assert cabe_en_limite(100, None)
    assert cabe_en_limite(2, 3) and not cabe_en_limite(3, 3)
    assert quedan_administradores(1) and not quedan_administradores(0)


def test_agrupa_por_modulo_aunque_reciba_un_generador():
    grupos = agrupar_por_modulo(p for p in ["ventas.venta.ver", "inventario.stock.ver"])
    assert grupos == {"Inventario": ["inventario.stock.ver"], "Ventas": ["ventas.venta.ver"]}
