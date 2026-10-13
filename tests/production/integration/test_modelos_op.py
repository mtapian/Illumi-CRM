"""0005a, T2: la base refuerza las reglas de la OP (RF-PRD-15, 16, 36, 41; art. 7.3)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.infrastructure.models import Almacen
from production.infrastructure.models import OpComponente, OrdenProduccion

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 12)


@pytest.fixture
def base(empresa_produccion):
    _, actor = empresa_produccion
    almacen = Almacen.objects.get(nombre="Principal")
    return (
        actor,
        almacen,
        Producto.objects.get(sku="GRA-IPA"),
        Producto.objects.get(sku="INS-MALTA"),
    )


def orden(base, numero=1, **kw):
    actor, almacen, granel, _ = base
    return OrdenProduccion.objects.create(
        numero=numero,
        producto=granel,
        fecha_programada=HOY,
        almacen_origen=almacen,
        almacen_destino=almacen,
        responsable_id=actor.usuario_id,
        **{"cantidad": D("500")} | kw,
    )


FINALIZADA = {"estado": "FINALIZADA", "fecha_fin": HOY, "finalizada_en": timezone.now()}


def falla(excepcion, crear):
    with transaction.atomic(), pytest.raises(excepcion):
        crear()


def test_numero_unico_y_cantidad_positiva(base):
    orden(base)
    falla(IntegrityError, lambda: orden(base))
    falla(IntegrityError, lambda: orden(base, 2, cantidad=D("0")))
    falla(IntegrityError, lambda: orden(base, 3, costo_indirecto=D("-1")))


def test_finalizada_con_producido_lote_y_costo_o_lote_perdido(base):
    """RF-PRD-41 y 15."""
    falla(IntegrityError, lambda: orden(base, 1, estado="FINALIZADA"))
    falla(IntegrityError, lambda: orden(base, 2, **FINALIZADA, cantidad_producida=D("425")))
    orden(
        base,
        3,
        **FINALIZADA,
        cantidad_producida=D("425"),
        lote_codigo="GRA-IPA-0001",
        costo_total=D("850"),
        costo_unitario=D("2"),
    )
    perdida = {"cantidad_producida": D("0"), "costo_total": D("790")}
    falla(IntegrityError, lambda: orden(base, 4, **FINALIZADA, **perdida, perdida=D("790")))
    falla(IntegrityError, lambda: orden(base, 5, **FINALIZADA, **perdida, motivo_perdida="x"))
    orden(base, 6, **FINALIZADA, **perdida, motivo_perdida="Contaminación", perdida=D("790"))


def test_anulada_con_motivo(base):
    """RF-PRD-16."""
    falla(IntegrityError, lambda: orden(base, 1, estado="ANULADA", anulada_en=timezone.now()))
    orden(base, 2, estado="ANULADA", anulada_en=timezone.now(), motivo_anulacion="Cancelada")


def test_componentes_unicos_no_negativos_y_bloqueados_al_finalizar(base):
    """RF-PRD-37, 38; los componentes de una OP Finalizada o Anulada no cambian."""
    malta = base[3]
    op = orden(base)

    def componente(**kw):
        return OpComponente.objects.create(op=op, producto=malta, por_consumir=D("100"), **kw)

    c = componente()
    falla(IntegrityError, lambda: componente())
    c.consumido = D("102")
    c.save()
    OrdenProduccion.objects.filter(pk=op.pk).update(
        **FINALIZADA,
        cantidad_producida=D("425"),
        lote_codigo="L",
        costo_total=D("1"),
        costo_unitario=D("1"),
    )
    with transaction.atomic(), pytest.raises(DatabaseError):
        OpComponente.objects.filter(pk=c.pk).update(consumido=D("1"))
    with transaction.atomic(), pytest.raises(DatabaseError):
        OpComponente.objects.filter(pk=c.pk).delete()
