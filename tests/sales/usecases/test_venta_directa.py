"""0006b, T5: venta directa (RF-VEN-18, 29, 52)."""

import uuid
from decimal import Decimal as D

import pytest

from sales.application import facturacion as uf
from sales.domain.errores import PedidoInvalido
from sales.domain.pedido import LineaPedido
from sales.infrastructure.contenedor import caso_de_venta_directa, sembrar_metodos_pago
from sales.infrastructure.models import Cobranza, MetodoPago, Pago, Pedido
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado
from tests.sales.usecases.test_facturacion import HOY, preparar, salidas

pytestmark = pytest.mark.django_db


@pytest.fixture
def v(empresa_ventas):
    empresa, actor = empresa_ventas
    v = preparar(empresa, actor)
    sembrar_metodos_pago(empresa.id, actor.usuario_id, HOY)
    v["metodo"] = {m.nombre: m.id for m in MetodoPago.objects.all()}
    return v


def vender(v, cantidad="24", pagos=(("Efectivo", "200.00"), ("Yape", "88.00")), **kw):
    datos = uf.DatosVentaDirecta(
        cliente_id=kw.get("cliente_id", v["clientes"]["varios"]),
        almacen_id=v["almacen"],
        lineas=(LineaPedido(v["ids"]["TER-IPA-330"], D(cantidad), D("12")),),
        pagos=tuple((v["metodo"][m], D(monto)) for m, monto in pagos),
        token=kw.get("token", uuid.uuid4()),
    )
    return caso_de_venta_directa().ejecutar(kw.get("actor", v["actor"]), datos, HOY)


def test_venta_directa_con_dos_pagos(v):
    """RF-VEN-18: pedido Facturado y Entregado, cobranza Pagada, una transacción."""
    id_ = vender(v)
    p = Pedido.objects.get(pk=id_)
    assert (p.estado, p.comprobante, p.forma_pago, p.total) == (
        "ENTREGADO", "BOLETA", "CONTADO", D("288.00")
    )  # fmt: skip
    assert (p.fecha_entrega, p.fecha_emision, p.cliente.es_generico) == (HOY, HOY, True)
    assert salidas(id_) == [("IPA-0015", D("10")), ("IPA-0020", D("14"))]
    c = Cobranza.objects.get(pedido_id=id_)
    assert (c.estado, c.pagado) == ("PAGADA", D("288.00"))
    assert sorted(Pago.objects.values_list("monto", flat=True)) == [D("88.00"), D("200.00")]


def test_los_pagos_deben_sumar_el_total(v):
    """RF-VEN-52: no se registra nada."""
    with pytest.raises(
        PedidoInvalido, match=r"Los pagos \(300.00\) deben sumar el total \(288.00\)"
    ):
        vender(v, pagos=(("Efectivo", "300.00"),))
    assert not Pedido.objects.exists() and not Cobranza.objects.exists()


def test_si_falla_al_facturar_no_queda_nada(v):
    """RF-VEN-18 y 26: una sola transacción."""
    with pytest.raises(PedidoInvalido, match="Stock insuficiente"):
        vender(
            v, cantidad="2000", pagos=(("Efectivo", "24000.00"),), cliente_id=v["clientes"]["bar"]
        )
    assert not Pedido.objects.exists() and salidas(1) == []


def test_doble_envio_registra_una_sola_venta(v):
    """RF-VEN-29: el mismo token devuelve la venta ya registrada."""
    token = uuid.uuid4()
    assert vender(v, token=token) == vender(v, token=token)
    assert Pedido.objects.count() == 1 and Pago.objects.count() == 2


def test_permiso(v):
    """RF-VEN-18: `ventas.venta.registrar`."""
    a = v["actor"]
    sin = Actor(a.usuario_id, a.empresa_id, a.permisos - {uf.REGISTRAR})
    with pytest.raises(AccesoDenegado):
        vender(v, actor=sin)
