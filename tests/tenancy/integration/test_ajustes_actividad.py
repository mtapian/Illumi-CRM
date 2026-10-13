"""T6 y T7: ajustes por empresa, actividad y habilitaciones de la BD (RF-TEN-22, 23, 29, 30)."""

from datetime import date, timedelta

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from tenancy.infrastructure.contenedor import tenancy_service
from tenancy.infrastructure.models import Actividad, EmpresaAjuste, PlanFuncionalidad

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


def test_un_solo_ajuste_activo_por_funcionalidad(crear_empresa):
    empresa = crear_empresa()
    datos = dict(empresa=empresa, funcionalidad_id="inventario.multialmacen", motivo="Prueba")
    EmpresaAjuste.objects.create(tipo="AGREGAR", **datos)
    with pytest.raises(IntegrityError), transaction.atomic():
        EmpresaAjuste.objects.create(tipo="QUITAR", **datos)


def test_la_actividad_es_de_solo_insercion(crear_empresa):
    actividad = Actividad.objects.create(empresa=crear_empresa(), accion="SUSPENDER", motivo="x")
    with pytest.raises(DatabaseError, match="solo inserción"), transaction.atomic():
        Actividad.objects.filter(pk=actividad.pk).update(motivo="y")
    with pytest.raises(DatabaseError, match="solo inserción"), transaction.atomic():
        actividad.delete()


def test_habilitaciones_son_el_plan_mas_y_menos_los_ajustes_vigentes(crear_empresa):
    empresa = crear_empresa()
    for codigo in ("catalogo.productos", "inventario.stock", "inventario.ajustes"):
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=codigo)
    EmpresaAjuste.objects.create(
        empresa=empresa, funcionalidad_id="inventario.ajustes", tipo="QUITAR", motivo="x"
    )
    EmpresaAjuste.objects.create(
        empresa=empresa,
        funcionalidad_id="inventario.lotes",
        tipo="AGREGAR",
        motivo="x",
        vigente_hasta=HOY,
    )
    hab = tenancy_service().habilitaciones_de(empresa.id, HOY)
    assert {"inventario.stock", "inventario.lotes", "core.admin"} <= hab
    assert "inventario.ajustes" not in hab
    assert "inventario.lotes" not in tenancy_service().habilitaciones_de(
        empresa.id, HOY + timedelta(1)
    )


def test_el_plan_de_prueba_incluye_todo(crear_empresa):
    """PRD Q8 (resuelta): el plan de prueba incluye todas las funcionalidades."""
    empresa = crear_empresa()
    empresa.plan.es_plan_prueba = True
    empresa.plan.save()
    assert "produccion.op" in tenancy_service().habilitaciones_de(empresa.id, HOY)
