"""T14: dos administradores se desactivan entre sí a la vez; uno es rechazado (RF-TEN-12)."""

import threading
from datetime import date

import pytest
from django.db import connection

from tenancy.application.usuarios import AsignarRoles, CambiarEstadoUsuario
from tenancy.domain.errores import UltimoAdministrador
from tenancy.infrastructure.contenedor import actor_de, caso_de_uso, sembrador_roles
from tenancy.infrastructure.models import Rol, Usuario

HOY = date(2026, 10, 10)


@pytest.mark.django_db(transaction=True)
def test_uno_de_los_dos_es_rechazado(crear_empresa):
    empresa = crear_empresa()
    lucia = Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa)
    jose = Usuario.objects.create_user("jose@andina.pe", "x", empresa=empresa)
    sembrador_roles()(empresa.id, lucia.id, HOY)
    admin = Rol.all_tenants.get(empresa=empresa, es_sistema=True).id
    caso_de_uso(AsignarRoles).ejecutar(actor_de(lucia, HOY), jose.id, [admin], HOY)
    actores = {lucia.id: actor_de(lucia, HOY), jose.id: actor_de(jose, HOY)}
    errores, barrera = [], threading.Barrier(2)

    def desactivar(actor, otro):
        try:
            barrera.wait()
            caso_de_uso(CambiarEstadoUsuario).ejecutar(actor, otro, False)
        except UltimoAdministrador as e:
            errores.append(e)
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=desactivar, args=(actores[lucia.id], jose.id)),
        threading.Thread(target=desactivar, args=(actores[jose.id], lucia.id)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(errores) == 1
    assert Usuario.objects.filter(is_active=True).count() == 1
