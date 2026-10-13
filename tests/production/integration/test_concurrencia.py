"""0005a, T6: dos usuarios finalizan la misma OP a la vez; se consume una sola vez
(RF-PRD-12). Con transacciones reales: cada hilo usa su propia conexión."""

import threading
from decimal import Decimal as D

import pytest
from django.db import connection

from inventory.infrastructure.models import Movimiento, Stock
from production.domain.errores import OpInvalida
from shared.domain.tenant import tenant_context
from tests.production.usecases.test_finalizar import ej, finalizar, op_en_proceso  # noqa: F401


@pytest.mark.django_db(transaction=True)
def test_doble_finalizacion_concurrente_consume_una_vez(ej, empresa_produccion):  # noqa: F811
    empresa, _ = empresa_produccion
    op_id = op_en_proceso(ej, "GRA-IPA", "500")
    barrera, resultados = threading.Barrier(2), []

    def cerrar():
        try:
            with tenant_context(empresa.id):
                barrera.wait(timeout=5)
                finalizar(ej, op_id, "425")
            resultados.append("ok")
        except OpInvalida as e:
            resultados.append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=cerrar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)
    assert sorted(resultados) == ["La OP está finalizada", "ok"]
    assert Movimiento.objects.filter(ref_tipo="OP", ref_id=op_id, tipo="ENTRADA").count() == 1
    malta = ej[2]["INS-MALTA"]
    assert sum(s.cantidad for s in Stock.objects.filter(producto_id=malta)) == D("200")
