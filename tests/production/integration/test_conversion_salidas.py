"""0005a enmienda 1, T12: cada OP existente pasa su producto a una salida con lo producido,
el lote y el costo, y sus componentes quedan asignados a ella; reversible (RF-PRD-49, 51)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

ANTES = [("production", "0001_ordenes")]


def _migrar(destino=None):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    destino = destino or executor.loader.graph.leaf_nodes()
    executor.migrate(destino)
    return executor.loader.project_state(destino).apps


@pytest.mark.django_db(transaction=True)
def test_convierte_la_op_a_una_salida_y_vuelve(crear_empresa):
    empresa = crear_empresa()
    apps = _migrar(ANTES)
    Unidad, Producto = apps.get_model("catalog", "Unidad"), apps.get_model("catalog", "Producto")
    und = Unidad.all_tenants.create(
        empresa_id=empresa.id, nombre="U", abreviatura="UND", codigo_sunat="NIU"
    )

    def producto(sku):
        return Producto.all_tenants.create(empresa_id=empresa.id, sku=sku, nombre=sku, unidad=und)

    granel, malta = producto("GRA"), producto("MALTA")
    almacen = apps.get_model("inventory", "Almacen").all_tenants.create(
        empresa_id=empresa.id, nombre="P"
    )
    Orden = apps.get_model("production", "OrdenProduccion")
    op = Orden.all_tenants.create(
        empresa_id=empresa.id,
        numero=1,
        producto=granel,
        cantidad=D("500"),
        fecha_programada=date(2026, 10, 12),
        almacen_origen=almacen,
        almacen_destino=almacen,
    )
    apps.get_model("production", "OpComponente").all_tenants.create(
        empresa_id=empresa.id,
        op=op,
        producto=malta,
        por_consumir=D("100"),
        consumido=D("102"),
        costo=D("408"),
    )
    Orden.all_tenants.filter(pk=op.pk).update(
        estado="FINALIZADA",
        fecha_fin=date(2026, 10, 12),
        cantidad_producida=D("425"),
        lote_codigo="GRA-0001",
        costo_total=D("850"),
        costo_unitario=D("2"),
        finalizada_en=timezone.now(),
    )

    apps = _migrar()
    salida = apps.get_model("production", "OpSalida").all_tenants.get(op_id=op.pk)
    assert (salida.producto_id, salida.cantidad, salida.factor, salida.producida) == (
        granel.id,
        D("500.0000"),
        D("1.0000"),
        D("425.0000"),
    )
    assert (salida.lote_codigo, salida.costo_total, salida.costo_unitario) == (
        "GRA-0001",
        D("850.00"),
        D("2.000000"),
    )
    componente = apps.get_model("production", "OpComponente").all_tenants.get(op_id=op.pk)
    assert componente.salida_id == salida.id

    apps = _migrar(ANTES)
    vuelta = apps.get_model("production", "OrdenProduccion").all_tenants.get(pk=op.pk)
    assert (vuelta.producto_id, vuelta.cantidad_producida, vuelta.lote_codigo) == (
        granel.id,
        D("425.0000"),
        "GRA-0001",
    )
    _migrar()
