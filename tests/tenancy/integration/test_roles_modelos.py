"""T5 y T6: roles por empresa y roles iniciales al registrar (RF-TEN-01, 10, 35)."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from shared.domain.tenant import tenant_context
from tenancy.application.registro import DatosRegistro
from tenancy.infrastructure.contenedor import registrar_empresa
from tenancy.infrastructure.models import Plan, Rol, Usuario

pytestmark = pytest.mark.django_db


def test_nombre_unico_por_empresa_y_un_solo_rol_de_sistema(crear_empresa):
    empresa = crear_empresa()
    with tenant_context(empresa.id):
        Rol.objects.create(nombre="Ventas")
        with pytest.raises(IntegrityError), transaction.atomic():
            Rol.objects.create(nombre="Ventas")
        Rol.objects.create(nombre="Administrador", es_sistema=True)
        with pytest.raises(IntegrityError), transaction.atomic():
            Rol.objects.create(nombre="Otro admin", es_sistema=True)


def test_al_registrar_se_crean_los_roles_iniciales_y_el_primer_usuario_es_administrador():
    Plan.objects.create(nombre="Prueba", slug="prueba", es_plan_prueba=True)
    datos = DatosRegistro(
        "20601234565", "Andina S.A.C.", "", "Lucía", "lucia@andina.pe", "Clave-Segura-2026"
    )
    resultado = registrar_empresa().ejecutar(datos, date(2026, 10, 10))
    with tenant_context(resultado.empresa_id):
        roles = {r.nombre: r for r in Rol.objects.all()}
        assert set(roles) == {"Administrador", "Gerente", "Producción", "Almacén", "Ventas"}
        assert roles["Administrador"].es_sistema and not roles["Gerente"].es_sistema
        admin = Usuario.objects.get(pk=resultado.admin_id)
        assert [r.nombre for r in admin.roles.all()] == ["Administrador"]
        assert roles["Gerente"].permisos.filter(permiso="ventas.venta.anular").exists()
