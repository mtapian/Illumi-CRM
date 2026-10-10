"""T1 a T3: auditoría de accesos inmutable, de roles y de usuarios (RF-TEN-43; RN-TEN-14)."""

from datetime import date

import pytest
from django.db import DatabaseError, transaction

from shared.domain.tenant import tenant_context
from tenancy.application import roles, usuarios
from tenancy.infrastructure.contenedor import actor_de, caso_de_uso
from tenancy.infrastructure.models import AuditoriaAcceso, Rol, Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


@pytest.fixture
def lucia(crear_empresa):
    empresa = crear_empresa()
    empresa.plan.es_plan_prueba = True
    empresa.plan.save()
    return asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))


def auditorias(usuario, entidad):
    with tenant_context(usuario.empresa_id):
        return list(AuditoriaAcceso.objects.filter(entidad=entidad).order_by("id"))


def test_la_auditoria_no_se_modifica_ni_se_borra(lucia):
    with tenant_context(lucia.empresa_id):
        fila = AuditoriaAcceso.objects.create(entidad="ROL", entidad_id=1, accion="CREAR")
        with pytest.raises(DatabaseError, match="solo inserción"), transaction.atomic():
            AuditoriaAcceso.objects.filter(pk=fila.pk).update(accion="X")
        with pytest.raises(DatabaseError, match="solo inserción"), transaction.atomic():
            fila.delete()


def test_se_auditan_los_cambios_de_roles(lucia):
    actor = actor_de(lucia, HOY)
    rol = caso_de_uso(roles.CrearRol).ejecutar(actor, "Cocina", {"produccion.op.ver"}, HOY)
    caso_de_uso(roles.EditarRol).ejecutar(actor, rol, "Cocina", {"produccion.op.ejecutar"}, HOY)
    caso_de_uso(roles.DuplicarRol).ejecutar(actor, rol, "Cocina 2", HOY)
    caso_de_uso(roles.CambiarEstadoRol).ejecutar(actor, rol, False)
    filas = auditorias(lucia, "ROL")
    assert [f.accion for f in filas] == ["CREAR", "EDITAR", "CREAR", "DESACTIVAR"]
    editar = filas[1]
    assert editar.antes["permisos"] == ["produccion.op.ver"]
    assert editar.despues["permisos"] == ["produccion.op.ejecutar"]
    assert editar.actor == lucia
    assert (filas[3].antes, filas[3].despues) == ({"activo": True}, {"activo": False})


def test_se_auditan_asignaciones_y_estado_de_usuarios(lucia):
    actor = actor_de(lucia, HOY)
    with tenant_context(lucia.empresa_id):
        ventas, gerente = (Rol.objects.get(nombre=n).id for n in ("Ventas", "Gerente"))
    ana = caso_de_uso(usuarios.CrearUsuario).ejecutar(actor, "Ana", "ana@a.pe", "x", [ventas], HOY)
    caso_de_uso(usuarios.AsignarRoles).ejecutar(actor, ana, [gerente], HOY)
    caso_de_uso(usuarios.CambiarEstadoUsuario).ejecutar(actor, ana, False)
    asignaciones = auditorias(lucia, "USUARIO_ROL")
    assert [(a.antes, a.despues) for a in asignaciones] == [
        ({"roles": []}, {"roles": ["Ventas"]}),
        ({"roles": ["Ventas"]}, {"roles": ["Gerente"]}),
    ]
    (estado,) = auditorias(lucia, "USUARIO")
    assert (estado.antes, estado.despues, estado.entidad_id) == (
        {"activo": True},
        {"activo": False},
        ana,
    )
