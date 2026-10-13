"""0006b, T2: la base refuerza la facturación y la cobranza (RF-VEN-17, 19, 29, 53 a 59)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from catalog.infrastructure.models import Producto
from inventory.infrastructure.models import Almacen
from sales.infrastructure.contenedor import sembrar_metodos_pago
from sales.infrastructure.models import (
    Cliente,
    Cobranza,
    Cuota,
    MetodoPago,
    Pago,
    Pedido,
    PedidoLinea,
)
from shared.domain.accesos import PERMISOS
from tenancy.domain.plantillas import PLANTILLAS

HOY = date(2026, 12, 1)
METODOS = ["Efectivo", "Yape", "Plin", "Tarjeta", "Transferencia"]


def falla(excepcion, accion):
    with transaction.atomic(), pytest.raises(excepcion):
        accion()


def test_permisos_de_cobranza():
    """RF-VEN-53 y 54: en la funcionalidad "Ventas" y en las plantillas Ventas y Gerente."""
    for p in ("ventas.cobranza.ver", "ventas.cobranza.gestionar"):
        assert PERMISOS[p] == "ventas.ventas"
        assert p in PLANTILLAS["Ventas"] and p in PLANTILLAS["Gerente"]


@pytest.mark.django_db
def test_metodos_de_pago(empresa_ventas):
    """RF-VEN-58 y 59: sembrados, nombre único sin mayúsculas."""
    empresa, _ = empresa_ventas
    sembrar_metodos_pago(empresa.id, None, HOY)
    sembrar_metodos_pago(empresa.id, None, HOY)  # idempotente
    assert sorted(MetodoPago.objects.values_list("nombre", flat=True)) == sorted(METODOS)
    falla(IntegrityError, lambda: MetodoPago.objects.create(nombre="yape"))


def _facturado(cliente, **kw):
    datos = {
        "numero": 1,
        "cliente": cliente,
        "fecha_entrega": HOY,
        "estado": "FACTURADO",
        "comprobante": "FACTURA",
        "forma_pago": "CONTADO",
        "fecha_emision": HOY,
        "almacen": Almacen.objects.get(nombre="Principal"),
    }
    return Pedido.objects.create(**(datos | kw))


@pytest.mark.django_db
def test_pedido_facturado(empresa_ventas):
    """RF-VEN-17 y 19: facturado con comprobante, forma de pago y emisión; boleta al contado;
    entregado con fecha; token único (RF-VEN-29)."""
    cliente = Cliente.objects.get(es_generico=True)
    falla(IntegrityError, lambda: _facturado(cliente, comprobante=""))
    falla(IntegrityError, lambda: _facturado(cliente, fecha_emision=None))
    falla(IntegrityError, lambda: _facturado(cliente, comprobante="BOLETA", forma_pago="CREDITO"))
    falla(IntegrityError, lambda: _facturado(cliente, comprobante="OTRO"))
    falla(IntegrityError, lambda: _facturado(cliente, estado="ENTREGADO"))
    _facturado(cliente, token="0f8fad5b-d9cb-469f-a165-70867728950e")
    falla(
        IntegrityError,
        lambda: _facturado(cliente, numero=2, token="0f8fad5b-d9cb-469f-a165-70867728950e"),
    )


@pytest.mark.django_db
def test_lineas_al_facturar(empresa_ventas):
    """RF-VEN-21 y 22: el desglose y el costo se escriben con el pedido Aprobado, y nada más;
    valor + ISC + IGV = subtotal."""
    cliente = Cliente.objects.get(es_generico=True)
    ipa = Producto.objects.get(sku="TER-IPA-330")
    p = Pedido.objects.create(numero=1, cliente=cliente, fecha_entrega=HOY)
    x = PedidoLinea.objects.create(
        pedido=p, producto=ipa, cantidad=D("24"), precio=D("12"), subtotal=D("288.00")
    )
    Pedido.objects.filter(pk=p.pk).update(estado="APROBADO")
    lineas = PedidoLinea.objects.filter(pk=x.pk)
    falla(IntegrityError, lambda: lineas.update(valor=D("244.07"), isc=0, igv=D("43.93")))
    falla(
        IntegrityError,
        lambda: lineas.update(valor=D("244.07"), isc=0, igv=D("40"), costo=D("45.43")),
    )
    lineas.update(valor=D("244.07"), isc=0, igv=D("43.93"), costo=D("45.43"))
    falla(DatabaseError, lambda: lineas.update(cantidad=D("25")))
    Pedido.objects.filter(pk=p.pk).update(
        estado="FACTURADO",
        comprobante="BOLETA",
        forma_pago="CONTADO",
        fecha_emision=HOY,
        almacen=Almacen.objects.get(nombre="Principal"),
    )
    falla(DatabaseError, lambda: lineas.update(costo=D("1")))


@pytest.mark.django_db
def test_cobranza_cuotas_y_pagos(empresa_ventas):
    """RF-VEN-53 a 57: pagado entre 0 y el total, Pagada solo si pagado = total; cuotas
    inmutables; pagos > 0, sin borrar, anulados con fecha y motivo."""
    empresa, _ = empresa_ventas
    sembrar_metodos_pago(empresa.id, None, HOY)
    cliente = Cliente.objects.get(es_generico=True)
    p = _facturado(cliente)

    def cobranza(**kw):
        datos = {"pedido": p, "cliente": cliente, "emision": HOY, "total": D("288.00")}
        return Cobranza.objects.create(**(datos | kw))

    falla(IntegrityError, lambda: cobranza(pagado=D("300")))
    falla(IntegrityError, lambda: cobranza(estado="PAGADA"))
    falla(IntegrityError, lambda: cobranza(pagado=D("288.00")))  # Pendiente con todo pagado
    c = cobranza()
    falla(IntegrityError, lambda: cobranza())  # una por pedido

    cuota = Cuota.objects.create(cobranza=c, numero=1, monto=D("288.00"), vencimiento=HOY)
    falla(
        IntegrityError, lambda: Cuota.objects.create(cobranza=c, numero=2, monto=0, vencimiento=HOY)
    )
    falla(DatabaseError, lambda: Cuota.objects.filter(pk=cuota.pk).update(monto=D("1")))
    falla(DatabaseError, lambda: Cuota.objects.filter(pk=cuota.pk).delete())

    efectivo = MetodoPago.objects.get(nombre="Efectivo")

    def pago(**kw):
        return Pago.objects.create(**({"cobranza": c, "metodo": efectivo, "fecha": HOY} | kw))

    falla(IntegrityError, lambda: pago(monto=D("0")))
    x = pago(monto=D("100"))
    pagos = Pago.objects.filter(pk=x.pk)
    falla(IntegrityError, lambda: pagos.update(motivo_anulacion="Error"))  # sin fecha
    falla(DatabaseError, lambda: pagos.update(monto=D("50")))
    falla(DatabaseError, lambda: pagos.delete())
    falla(DatabaseError, lambda: MetodoPago.objects.filter(pk=efectivo.pk).delete())


ANTES = [("sales", "0001_clientes_pedidos")]


def _migrar(destino=None):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    destino = destino or executor.loader.graph.leaf_nodes()
    executor.migrate(destino)
    return executor.loader.project_state(destino).apps


@pytest.mark.django_db(transaction=True)
def test_empresas_y_roles_existentes(crear_empresa):
    """RF-VEN-58: las empresas existentes reciben los métodos de pago; los roles que ya
    registran ventas reciben los permisos de cobranza. Reversible."""
    empresa = crear_empresa()
    apps = _migrar(ANTES)
    Rol, RolPermiso = apps.get_model("tenancy", "Rol"), apps.get_model("tenancy", "RolPermiso")
    vende = Rol.all_tenants.create(empresa_id=empresa.id, nombre="Mostrador")
    RolPermiso.objects.create(rol=vende, permiso_id="ventas.venta.registrar")
    otro = Rol.all_tenants.create(empresa_id=empresa.id, nombre="Planta")

    apps = _migrar()
    MetodoPago = apps.get_model("sales", "MetodoPago")
    assert sorted(
        MetodoPago.all_tenants.filter(empresa_id=empresa.id).values_list("nombre", flat=True)
    ) == sorted(METODOS)
    RolPermiso = apps.get_model("tenancy", "RolPermiso")

    def de(rol):
        return set(RolPermiso.objects.filter(rol_id=rol.id).values_list("permiso_id", flat=True))

    assert {"ventas.cobranza.ver", "ventas.cobranza.gestionar"} <= de(vende)
    assert not de(otro)
    _migrar(ANTES)
    _migrar()
