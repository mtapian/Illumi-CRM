"""0005a, T2 y enmienda 1 (T12): la base refuerza las reglas de la OP y sus salidas
(RF-PRD-15, 16, 36, 41, 49, 51; art. 7.3)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.infrastructure.models import Almacen
from production.infrastructure.models import OpComponente, OpSalida, OrdenProduccion

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 12)
FINALIZADA = {"estado": "FINALIZADA", "fecha_fin": HOY, "finalizada_en": timezone.now()}


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
    actor, almacen, _, _ = base
    return OrdenProduccion.objects.create(
        numero=numero,
        fecha_programada=HOY,
        almacen_origen=almacen,
        almacen_destino=almacen,
        responsable_id=actor.usuario_id,
        **kw,
    )


def falla(excepcion, crear):
    with transaction.atomic(), pytest.raises(excepcion):
        crear()


def test_numero_unico_e_indirecto_no_negativo(base):
    orden(base)
    falla(IntegrityError, lambda: orden(base))
    falla(IntegrityError, lambda: orden(base, 3, costo_indirecto=D("-1")))


def test_finalizada_con_fecha_y_lote_perdido_con_motivo(base):
    """RF-PRD-41 y 15."""
    falla(IntegrityError, lambda: orden(base, 1, estado="FINALIZADA"))
    orden(base, 2, **FINALIZADA, costo_total=D("850"))
    falla(
        IntegrityError, lambda: orden(base, 3, **FINALIZADA, costo_total=D("790"), perdida=D("790"))
    )
    falla(
        IntegrityError,
        lambda: orden(base, 4, **FINALIZADA, costo_total=D("790"), motivo_perdida="x"),
    )
    orden(
        base,
        5,
        **FINALIZADA,
        costo_total=D("790"),
        perdida=D("790"),
        motivo_perdida="Contaminación",
    )


def test_anulada_con_motivo(base):
    """RF-PRD-16."""
    falla(IntegrityError, lambda: orden(base, 1, estado="ANULADA", anulada_en=timezone.now()))
    orden(base, 2, estado="ANULADA", anulada_en=timezone.now(), motivo_anulacion="Cancelada")


def test_salidas_validas_unicas_y_con_lote_si_producen(base):
    """RF-PRD-49, 52."""
    granel = base[2]
    op = orden(base)

    def salida(**kw):
        return OpSalida.objects.create(op=op, producto=granel, **{"cantidad": D("500")} | kw)

    falla(IntegrityError, lambda: salida(factor=D("0")))
    falla(IntegrityError, lambda: salida(cantidad=D("0")))
    falla(IntegrityError, lambda: salida(producida=D("425")))  # sin lote ni costo
    salida(producida=D("425"), lote_codigo="L", costo_unitario=D("2"))
    falla(IntegrityError, lambda: salida())


def test_componentes_por_salida_y_bloqueados_al_finalizar(base):
    """RF-PRD-51: el mismo componente en dos salidas, no dos veces en la misma ni común."""
    _, _, granel, malta = base
    op = orden(base)
    s = OpSalida.objects.create(op=op, producto=granel, cantidad=D("500"))

    def componente(salida=None):
        return OpComponente.objects.create(
            op=op, producto=malta, por_consumir=D("1"), salida=salida
        )

    c = componente(s)
    componente()  # común
    falla(IntegrityError, lambda: componente(s))
    falla(IntegrityError, lambda: componente())
    OrdenProduccion.objects.filter(pk=op.pk).update(**FINALIZADA, costo_total=D("1"))
    with transaction.atomic(), pytest.raises(DatabaseError):
        OpComponente.objects.filter(pk=c.pk).update(consumido=D("1"))
    with transaction.atomic(), pytest.raises(DatabaseError):
        OpSalida.objects.filter(pk=s.pk).update(producida=D("1"))
