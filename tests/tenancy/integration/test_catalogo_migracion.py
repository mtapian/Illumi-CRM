"""T4 y T5: tablas del catálogo sincronizadas con `CATALOGO` (RF-TEN-25)."""

import pytest
from django.db import IntegrityError

from shared.domain.accesos import CATALOGO, PERMISOS
from tenancy.infrastructure.catalogo import sincronizar_catalogo
from tenancy.infrastructure.models import (
    Funcionalidad,
    FuncionalidadDependencia,
    Modulo,
    Permiso,
    Plan,
    PlanFuncionalidad,
)

pytestmark = pytest.mark.django_db


def test_despues_de_migrar_las_tablas_coinciden_con_el_catalogo():
    assert set(Funcionalidad.objects.values_list("codigo", flat=True)) == set(CATALOGO)
    assert set(Permiso.objects.values_list("codigo", flat=True)) == set(PERMISOS)
    assert Modulo.objects.filter(codigo="PRODUCCION").exists()
    assert FuncionalidadDependencia.objects.filter(
        funcionalidad_id="produccion.op", requiere_id="inventario.stock"
    ).exists()


def test_sincronizar_dos_veces_no_cambia_nada():
    antes = list(Funcionalidad.objects.order_by("codigo").values())
    sincronizar_catalogo()
    assert list(Funcionalidad.objects.order_by("codigo").values()) == antes


def test_un_codigo_retirado_queda_obsoleto_y_no_se_borra():
    Funcionalidad.objects.create(codigo="viejo.algo", nombre="Vieja", modulo_id="CORE")
    sincronizar_catalogo()
    assert Funcionalidad.objects.get(codigo="viejo.algo").obsoleto
    assert not Funcionalidad.objects.get(codigo="ventas.ventas").obsoleto


def test_plan_funcionalidad_tiene_pk_compuesta():
    plan = Plan.objects.create(nombre="Negocio", slug="negocio")
    PlanFuncionalidad.objects.create(plan=plan, funcionalidad_id="ventas.ventas")
    with pytest.raises(IntegrityError):
        PlanFuncionalidad.objects.create(plan=plan, funcionalidad_id="ventas.ventas")
