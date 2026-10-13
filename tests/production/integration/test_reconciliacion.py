"""0005a, T6: tras OP encadenadas (granel → envasado, con lotes perdidos), el kardex reproduce
el stock y el valor de cada producto (constitución, art. 4.6). Semillas fijas."""

import random
from decimal import Decimal as D

import pytest
from django.db import transaction
from django.db.models import Sum

from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import CostoProducto, Movimiento, Stock
from production.infrastructure.models import OrdenProduccion
from shared.domain.errores import DomainError
from tests.production.usecases.test_finalizar import HOY, ej, finalizar, op_en_proceso  # noqa: F401

pytestmark = pytest.mark.django_db


def total(filas, campo):
    return filas.aggregate(t=Sum(campo))["t"] or D("0")


@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_op_encadenadas_cuadran_con_el_kardex(ej, semilla):  # noqa: F811
    azar = random.Random(semilla)
    actor, almacen, ids = ej
    compras = ["INS-MALTA", "INS-MALTA-CAR", "INS-LUP-CS", "INS-LEV-US05", "ENV-BOT330"]
    for n in range(40):
        try:
            with transaction.atomic():
                paso = azar.random()
                if paso < 0.3:
                    sku = azar.choice(compras)
                    costo = D(azar.randint(1, 900_000)) / 100_000
                    linea = Linea(ids[sku], almacen, D(azar.randint(10, 3000)), costo)
                    inventario().registrar_entrada(
                        "COMPRA", "COMPRA", 100 + n, [linea], actor.usuario_id, HOY
                    )
                elif paso < 0.65:
                    op_id = op_en_proceso(ej, "GRA-IPA", str(azar.randint(20, 300)))
                    perdida = azar.random() < 0.15
                    producida = "0" if perdida else str(D(azar.randint(1500, 30000)) / 100)
                    finalizar(
                        ej, op_id, producida, motivo_perdida="Contaminación" if perdida else ""
                    )
                else:
                    op_id = op_en_proceso(ej, "TER-IPA-330", str(azar.randint(10, 400)))
                    finalizar(ej, op_id, str(azar.randint(5, 400)))
        except DomainError:
            pass  # faltantes de stock: la OP queda en proceso, sin movimientos

    finalizadas = OrdenProduccion.objects.filter(estado="FINALIZADA")
    assert finalizadas.filter(salidas__producto_id=ids["TER-IPA-330"]).count() > 3  # envasados
    for producto in ids.values():
        movs = Movimiento.objects.filter(producto_id=producto)
        if not movs.exists():
            continue
        entradas, salidas = movs.filter(tipo="ENTRADA"), movs.filter(tipo="SALIDA")
        costo = CostoProducto.objects.get(producto_id=producto)
        cantidad = total(entradas, "cantidad") - total(salidas, "cantidad")
        valor = total(entradas, "costo_total") - total(salidas, "costo_total")
        assert (
            cantidad
            == costo.cantidad_total
            == total(Stock.objects.filter(producto_id=producto), "cantidad")
        )
        assert valor == costo.valor_total
    # El costo de cada OP finalizada es lo que salió de sus componentes (más el indirecto).
    for op in OrdenProduccion.objects.filter(estado="FINALIZADA"):
        salidas = Movimiento.objects.filter(ref_tipo="OP", ref_id=op.id, tipo="SALIDA")
        assert total(salidas, "costo_total") + op.costo_indirecto == op.costo_total
