"""T24 (RF-TEN-18 y 20): el cron marca VENCIDA sin borrar ningún dato."""

from datetime import date, timedelta

import pytest
from django.apps import apps
from django.core.management import call_command

from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import Empresa, Usuario

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


def conteos():
    return {m._meta.db_table: m._base_manager.count() for m in apps.get_models()}


def test_marca_vencidas_solo_las_que_pasaron_su_fecha_y_no_borra_nada(crear_empresa):
    vencida = crear_empresa("20601234565", fecha_termino=HOY - timedelta(days=1))
    al_dia = crear_empresa("20512345671", fecha_termino=HOY)
    suspendida = crear_empresa(
        "10456789124", estado=Estado.SUSPENDIDA, fecha_termino=HOY - timedelta(days=9)
    )
    Usuario.objects.create_user("ana@andina.pe", "Clave-Segura-2026", nombre="Ana", empresa=vencida)
    antes = conteos()

    call_command("vencer_suscripciones", hoy=HOY.isoformat())

    estados = dict(Empresa.objects.values_list("id", "estado"))
    assert estados[vencida.id] == Estado.VENCIDA
    assert estados[al_dia.id] == Estado.TRIAL
    assert estados[suspendida.id] == Estado.SUSPENDIDA
    assert conteos() == antes
