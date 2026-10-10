"""T12 a T18: usuarios y roles (RF-TEN-10 a 13, 35 a 38, 53; RN-TEN-04, 05, 11)."""

from datetime import date

import pytest

from shared.domain.errores import AccesoDenegado, NoEncontrado
from shared.domain.tenant import tenant_context
from tenancy.application import roles, usuarios
from tenancy.domain.errores import (
    EscaladaDePrivilegios,
    LimiteUsuariosPlan,
    PermisoNoHabilitado,
    RolConUsuarios,
    RolDeSistema,
    UltimoAdministrador,
)
from tenancy.infrastructure.contenedor import actor_de, caso_de_uso, sembrador_roles
from tenancy.infrastructure.models import Rol, Usuario

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


@pytest.fixture
def empresa(crear_empresa):
    empresa = crear_empresa()
    empresa.plan.es_plan_prueba = True  # todo habilitado
    empresa.plan.limite_usuarios = 3
    empresa.plan.save()
    return empresa


@pytest.fixture
def admin(empresa):
    usuario = Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa)
    sembrador_roles()(empresa.id, usuario.id, HOY)
    return usuario


def rol(empresa, nombre):
    return Rol.all_tenants.get(empresa=empresa, nombre=nombre).id


def crear(actor, email, *nombres_rol, empresa):
    ids = [rol(empresa, n) for n in nombres_rol]
    return caso_de_uso(usuarios.CrearUsuario).ejecutar(actor, email, email, "x", ids, HOY)


def test_crear_usuario_con_rol_y_limite_sin_contar_tecnicos(empresa, admin):
    actor = actor_de(admin, HOY)
    crear(actor, "mario@andina.pe", "Producción", empresa=empresa)
    Usuario.objects.create_user("n8n@andina.pe", "x", empresa=empresa, es_tecnico=True)
    crear(actor, "ana@andina.pe", "Ventas", empresa=empresa)
    with pytest.raises(LimiteUsuariosPlan, match="Tu plan permite hasta 3 usuarios activos"):
        crear(actor, "nuevo@andina.pe", "Ventas", empresa=empresa)


def test_reactivar_por_encima_del_limite_se_rechaza(empresa, admin):
    actor = actor_de(admin, HOY)
    mario = crear(actor, "mario@andina.pe", "Producción", empresa=empresa)
    cambiar = caso_de_uso(usuarios.CambiarEstadoUsuario)
    cambiar.ejecutar(actor, mario, False)
    crear(actor, "ana@andina.pe", "Ventas", empresa=empresa)
    crear(actor, "rosa@andina.pe", "Almacén", empresa=empresa)
    with pytest.raises(LimiteUsuariosPlan):
        cambiar.ejecutar(actor, mario, True)


def test_no_existe_operacion_de_borrado_de_usuarios():
    assert not [n for n in dir(usuarios) if "elimin" in n.lower() or "borr" in n.lower()]


def test_ultimo_administrador(empresa, admin):
    actor = actor_de(admin, HOY)
    with pytest.raises(UltimoAdministrador, match="al menos un administrador activo"):
        caso_de_uso(usuarios.CambiarEstadoUsuario).ejecutar(actor, admin.id, False)
    with pytest.raises(UltimoAdministrador):
        caso_de_uso(usuarios.AsignarRoles).ejecutar(actor, admin.id, [rol(empresa, "Gerente")], HOY)


def test_escalada_y_el_administrador_puede_asignar_cualquier_rol(empresa, admin):
    actor = actor_de(admin, HOY)
    jose = crear(actor, "jose@andina.pe", "Gerente", empresa=empresa)
    rol_usuarios = caso_de_uso(roles.CrearRol).ejecutar(
        actor, "Gestor de usuarios", {"core.usuario.gestionar"}, HOY
    )
    caso_de_uso(usuarios.AsignarRoles).ejecutar(
        actor, jose, [rol(empresa, "Gerente"), rol_usuarios], HOY
    )
    actor_jose = actor_de(Usuario.objects.get(pk=jose), HOY)
    asignar = caso_de_uso(usuarios.AsignarRoles)
    with pytest.raises(EscaladaDePrivilegios, match="Solo un administrador"):
        asignar.ejecutar(actor_jose, jose, [rol(empresa, "Administrador")], HOY)
    rol_roles = caso_de_uso(roles.CrearRol).ejecutar(
        actor, "Gestor de roles", {"core.rol.gestionar"}, HOY
    )
    with pytest.raises(EscaladaDePrivilegios, match="No puedes dar permisos que no tienes"):
        asignar.ejecutar(actor_jose, jose, [rol_roles], HOY)
    asignar.ejecutar(actor, jose, [rol(empresa, "Administrador")], HOY)


def test_no_se_ven_usuarios_ni_roles_de_otra_empresa(empresa, admin, crear_empresa):
    otra = crear_empresa(ruc="20100047218")
    ajeno = Usuario.objects.create_user("x@brew.pe", "x", empresa=otra)
    with pytest.raises(NoEncontrado):
        caso_de_uso(usuarios.EditarUsuario).ejecutar(actor_de(admin, HOY), ajeno.id, "Hack")


def test_sin_permiso_se_rechaza(empresa, admin):
    actor = actor_de(admin, HOY)
    ana = Usuario.objects.get(pk=crear(actor, "ana@andina.pe", "Ventas", empresa=empresa))
    with pytest.raises(AccesoDenegado):
        crear(actor_de(ana, HOY), "otro@andina.pe", "Ventas", empresa=empresa)


def test_roles_validan_habilitaciones_y_el_administrador_no_se_edita(empresa, admin):
    empresa.plan.es_plan_prueba = False
    empresa.plan.save()
    actor = actor_de(admin, HOY)
    with pytest.raises(PermisoNoHabilitado, match="produccion.op.ejecutar no está incluido"):
        caso_de_uso(roles.CrearRol).ejecutar(actor, "Cocina", {"produccion.op.ejecutar"}, HOY)
    for caso, args in (
        (roles.EditarRol, ("Admin", set(), HOY)),
        (roles.EliminarRol, ()),
        (roles.CambiarEstadoRol, (False,)),
    ):
        with pytest.raises(RolDeSistema):
            caso_de_uso(caso).ejecutar(actor, rol(empresa, "Administrador"), *args)


def test_rol_con_usuarios_no_se_elimina_y_editar_conserva_lo_no_habilitado(empresa, admin):
    actor = actor_de(admin, HOY)
    crear(actor, "ana@andina.pe", "Ventas", empresa=empresa)
    crear(actor, "rosa@andina.pe", "Ventas", empresa=empresa)
    with pytest.raises(RolConUsuarios, match="El rol tiene 2 usuarios; puedes desactivarlo"):
        caso_de_uso(roles.EliminarRol).ejecutar(actor, rol(empresa, "Ventas"))
    gerente = rol(empresa, "Gerente")
    empresa.plan.es_plan_prueba = False  # deja de estar habilitado todo salvo CORE
    empresa.plan.save()
    caso_de_uso(roles.EditarRol).ejecutar(
        actor_de(admin, HOY), gerente, "Gerente", {"core.dashboard.ver"}, HOY
    )
    with tenant_context(empresa.id):
        guardados = set(Rol.objects.get(pk=gerente).permisos.values_list("permiso", flat=True))
    assert "ventas.venta.anular" in guardados  # RF-TEN-39
