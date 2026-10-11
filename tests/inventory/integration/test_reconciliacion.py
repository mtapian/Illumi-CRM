"""0003a, T17: el kardex reproduce exactamente el stock y el valor (RNF-INV-01; constitución,
art. 4.6). Secuencias aleatorias de entradas, salidas (con y sin lote) y reversiones, con
semillas fijas para que un fallo se pueda repetir."""

import random
from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from django.db import transaction
from django.db.models import Sum

from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen, CostoProducto, Movimiento, Stock
from shared.domain.errores import DomainError

pytestmark = pytest.mark.django_db
HOY = date(2026, 11, 1)


def total(filas, campo):
    return filas.aggregate(t=Sum(campo))["t"] or D("0")


@pytest.mark.parametrize("semilla", [1, 2, 3, 4, 5])
def test_kardex_reproduce_stock_y_valor(inv, semilla):
    azar = random.Random(semilla)
    servicio, admin = inventario(), inv["admin"].id
    almacenes = [inv["principal"], Almacen.objects.create(nombre="Taproom").id]
    producto, refs = inv["ipa"], []
    for n in range(150):
        almacen, lote = azar.choice(almacenes), azar.choice([None, "L1", "L2", "L3", "L4"])
        cantidad = D(azar.randint(1, 4000)) / 100  # hasta 2 decimales: ejercita el redondeo
        costo = D(azar.randint(1, 9_999_999)) / 1_000_000
        vence = HOY + timedelta(days=azar.randint(-5, 60)) if lote else None
        operacion = azar.random()
        try:
            with transaction.atomic():
                if operacion < 0.45:
                    entrada = Linea(producto, almacen, cantidad, costo, lote, vence)
                    servicio.registrar_entrada("COMPRA", "COMPRA", n, [entrada], admin, HOY)
                    refs.append(("COMPRA", n))
                elif operacion < 0.75:
                    salida = Linea(producto, almacen, cantidad)
                    motivo = azar.choice(["VENTA", "MERMA"])
                    servicio.registrar_salida(motivo, "VENTA", n, [salida], admin, HOY)
                    refs.append(("VENTA", n))
                elif refs:
                    servicio.revertir(*azar.choice(refs), admin)
        except DomainError:
            pass  # stock insuficiente, entrada consumida, lote con otro vencimiento…

    movs = Movimiento.objects.filter(producto_id=producto)
    entradas, salidas = movs.filter(tipo="ENTRADA"), movs.filter(tipo="SALIDA")
    costo = CostoProducto.objects.get(producto_id=producto)
    cantidad = total(entradas, "cantidad") - total(salidas, "cantidad")
    valor = total(entradas, "costo_total") - total(salidas, "costo_total")
    assert movs.count() > 20
    # La secuencia ejercita reversiones, lotes y los dos almacenes.
    assert movs.filter(revierte__isnull=False).exists()
    assert movs.filter(lote__isnull=False).exists() and movs.filter(lote__isnull=True).exists()
    assert movs.values("almacen_id").distinct().count() == 2
    assert cantidad == costo.cantidad_total == total(Stock.objects.all(), "cantidad")
    assert valor == costo.valor_total
    ultimo = movs.order_by("id").last()
    assert (ultimo.saldo_cantidad, ultimo.saldo_promedio) == (
        costo.cantidad_total,
        costo.costo_promedio,
    )
    assert costo.cantidad_total > 0 or costo.valor_total == 0
    # El stock de cada almacén y lote coincide con sus movimientos.
    for s in Stock.objects.all():
        propios = movs.filter(almacen_id=s.almacen_id, lote_id=s.lote_id)
        neto = total(propios.filter(tipo="ENTRADA"), "cantidad") - total(
            propios.filter(tipo="SALIDA"), "cantidad"
        )
        assert neto == s.cantidad
