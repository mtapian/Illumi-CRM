"""0004b, T4: dos usuarios anulan la misma compra a la vez; se revierte una sola vez
(RF-COM-17). Con transacciones reales: cada hilo usa su propia conexión."""

import threading
from decimal import Decimal as D

import pytest
from django.db import connection

from inventory.infrastructure.models import CostoProducto, Movimiento
from purchasing.application import compras as uc
from purchasing.domain.errores import CompraInvalida
from purchasing.infrastructure.contenedor import caso_de_compra
from shared.domain.tenant import tenant_context
from tests.purchasing.usecases.test_compras import base, crear, finalizar  # noqa: F401


@pytest.mark.django_db(transaction=True)
def test_doble_anulacion_concurrente_revierte_una_vez(base, empresa_compras):  # noqa: F811
    empresa, _ = empresa_compras
    compra = crear(base)
    finalizar(base, compra)
    barrera, resultados = threading.Barrier(2), []

    def anular():
        try:
            with tenant_context(empresa.id):
                barrera.wait(timeout=5)
                caso_de_compra(uc.AnularCompra).ejecutar(base["actor"], compra, "Duplicada")
            resultados.append("ok")
        except CompraInvalida as e:
            resultados.append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=anular) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)
    assert sorted(resultados) == ["La compra ya está anulada", "ok"]
    assert Movimiento.objects.filter(ref_id=compra, motivo="ANULACION").count() == 1
    assert CostoProducto.objects.get(producto_id=base["malta"]).cantidad_total == D("0")
