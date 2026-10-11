"""0003a, T13: dos salidas a la vez por el último stock; solo una tiene éxito (RF-INV-19,
RN-GEN-02). Con transacciones reales: cada hilo usa su propia conexión."""

import threading
from datetime import date
from decimal import Decimal as D

import pytest
from django.db import connection, transaction

from inventory.application.servicio import Linea
from inventory.domain.errores import StockInsuficiente
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Movimiento, Stock
from shared.domain.tenant import tenant_context

HOY = date(2026, 11, 1)


@pytest.mark.django_db(transaction=True)
def test_dos_salidas_simultaneas_por_el_ultimo_stock(inv):
    malta, principal, admin = inv["malta"], inv["principal"], inv["admin"].id
    with transaction.atomic():  # el servicio corre dentro de la transacción de quien llama
        inventario().registrar_entrada(
            "SALDO_INICIAL", "AJUSTE", 1, [Linea(malta, principal, D("10"), D("4"))], admin, HOY
        )
    barrera, resultados = threading.Barrier(2), []

    def salida():
        try:
            with tenant_context(inv["empresa"].id), transaction.atomic():
                barrera.wait(timeout=5)
                linea = Linea(malta, principal, D("8"))
                inventario().registrar_salida("MERMA", "AJUSTE", 2, [linea], admin, HOY)
            resultados.append("ok")
        except StockInsuficiente as e:
            resultados.append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=salida) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)
    assert sorted(resultados) == [
        "Stock insuficiente de INS-MALTA en Principal: disponible 2.0000, requerido 8.0000",
        "ok",
    ]
    assert Stock.objects.get(producto_id=malta).cantidad == D("2.0000")
    assert Movimiento.objects.filter(tipo="SALIDA").count() == 1
