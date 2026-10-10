"""T8 a T14: casos de uso del super admin (RF-TEN-22, 23, 25 a 27, 29, 31 a 34)."""

from datetime import date

import pytest

from tenancy.application.operaciones_en_curso import ContadorOperacionesEnCurso
from tenancy.application.plataforma import Plataforma
from tenancy.domain.errores import (
    CoreNoSeQuita,
    DependenciasFaltantes,
    DependientesHabilitados,
    MotivoObligatorio,
)
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.contenedor import plataforma
from tenancy.infrastructure.models import Actividad, EmpresaAjuste, Plan, PlanFuncionalidad
from tenancy.infrastructure.repositorios import PlataformaOrm, funcionalidades_de_plan

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)
EMPRENDEDOR = {
    "catalogo.productos",
    "inventario.stock",
    "inventario.ajustes",
    "compras.compras",
    "ventas.clientes",
    "ventas.ventas",
    "finanzas.gastos",
}


@pytest.fixture
def empresa(crear_empresa):
    empresa = crear_empresa(estado=Estado.TRIAL)
    for f in EMPRENDEDOR:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    return empresa


def test_activar_plan_registra_la_actividad(empresa):
    negocio = Plan.objects.create(nombre="Negocio", slug="negocio")
    plataforma().activar_plan(empresa.id, negocio.id, date(2026, 12, 31), "Pago", None)
    empresa.refresh_from_db()
    assert (empresa.estado, empresa.plan, empresa.fecha_termino) == (
        Estado.ACTIVA,
        negocio,
        date(2026, 12, 31),
    )
    assert Actividad.objects.get(empresa=empresa).motivo == "Pago"


def test_suspender_y_reactivar_vuelve_al_estado_anterior(empresa):
    plataforma().suspender(empresa.id, "Falta de pago", None)
    empresa.refresh_from_db()
    assert empresa.estado == Estado.SUSPENDIDA
    plataforma().reactivar(empresa.id, "Pagó", None)
    empresa.refresh_from_db()
    assert empresa.estado == Estado.TRIAL


def test_toda_accion_exige_motivo(empresa):
    with pytest.raises(MotivoObligatorio, match="El motivo es obligatorio"):
        plataforma().suspender(empresa.id, "  ", None)


def test_configurar_plan_valida_dependencias_y_muestra_el_impacto(empresa):
    with pytest.raises(DependenciasFaltantes, match="requiere: Recetas, Órdenes de producción"):
        plataforma().configurar_plan(
            empresa.plan_id, EMPRENDEDOR | {"produccion.envasado"}, {}, confirmado=False
        )
    nuevas = EMPRENDEDOR | {"transversal.exportacion"}
    assert plataforma().configurar_plan(empresa.plan_id, nuevas, {}, confirmado=False) == 1
    assert "transversal.exportacion" not in funcionalidades_de_plan(empresa.plan_id)
    plataforma().configurar_plan(empresa.plan_id, nuevas, {"limite_usuarios": 5}, confirmado=True)
    assert "transversal.exportacion" in funcionalidades_de_plan(empresa.plan_id)
    assert Plan.objects.get(pk=empresa.plan_id).limite_usuarios == 5


def test_cambiar_plan_conserva_los_ajustes(empresa):
    plataforma().agregar(empresa.id, ["inventario.lotes"], "Piloto", None, None, HOY)
    negocio = Plan.objects.create(nombre="Negocio", slug="negocio")
    PlanFuncionalidad.objects.create(plan=negocio, funcionalidad_id="catalogo.productos")
    PlanFuncionalidad.objects.create(plan=negocio, funcionalidad_id="inventario.stock")
    plataforma().cambiar_plan(empresa.id, negocio.id, "Upgrade", None)
    hab = plataforma().habilitadas(empresa.id, HOY)
    assert {"inventario.stock", "inventario.lotes"} <= hab
    assert "ventas.ventas" not in hab


def test_agregar_valida_dependencias(empresa):
    with pytest.raises(DependenciasFaltantes, match="Envasado multipresentación requiere"):
        plataforma().agregar(empresa.id, ["produccion.envasado"], "x", None, None, HOY)


def test_quitar_rechaza_dependencias_y_core(empresa):
    with pytest.raises(
        DependientesHabilitados,
        match="No se puede quitar Stock y kardex: la requieren Ajustes de inventario, "
        "Compras y proveedores, Ventas",
    ):
        plataforma().quitar(empresa.id, ["inventario.stock"], "x", None, None, HOY, False)
    with pytest.raises(CoreNoSeQuita):
        plataforma().quitar(empresa.id, ["core.admin"], "x", None, None, HOY, True)


def test_quitar_con_operaciones_en_curso_advierte_antes_de_guardar(empresa):
    from django.db import transaction

    from tenancy.application.operaciones_en_curso import RegistroContadores

    registro = RegistroContadores()
    registro.registrar(
        ContadorOperacionesEnCurso(
            "produccion.op", lambda _: 2, "La empresa tiene {n} OP en proceso"
        )
    )
    p = Plataforma(PlataformaOrm(), registro, transaction.atomic)
    produccion = ["produccion.recetas", "produccion.op", "produccion.envasado"]
    p.agregar(empresa.id, produccion, "Piloto", None, None, HOY)
    assert p.quitar(empresa.id, produccion, "Fin", None, None, HOY, False) == [
        "La empresa tiene 2 OP en proceso"
    ]
    assert "produccion.op" in p.habilitadas(empresa.id, HOY)
    assert p.quitar(empresa.id, produccion, "Fin", None, None, HOY, True) == []
    assert "produccion.op" not in p.habilitadas(empresa.id, HOY)
    assert EmpresaAjuste.objects.filter(revocado_en__isnull=True, tipo="QUITAR").count() == 3
