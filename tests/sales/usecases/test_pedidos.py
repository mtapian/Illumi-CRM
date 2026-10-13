"""0006a, T6: casos de uso del pedido (RF-VEN-06 a 08, 11, 16, 37, 48)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import transaction

from catalog.infrastructure.models import Producto
from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen
from sales.application import pedidos as uc
from sales.domain.errores import PedidoInvalido
from sales.domain.pedido import LineaPedido
from sales.infrastructure.contenedor import caso_de_pedido
from sales.infrastructure.models import Cliente, Pedido
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado

pytestmark = pytest.mark.django_db
HOY = date(2026, 11, 10)


@pytest.fixture
def v(empresa_ventas):
    """48 TER-IPA-330 en stock; TER-IPA-20L sin stock."""
    _, actor = empresa_ventas
    ids = {p.sku: p.id for p in Producto.objects.all()}
    almacen = Almacen.objects.get(nombre="Principal").id
    with transaction.atomic():
        linea = Linea(ids["TER-IPA-330"], almacen, D("48"), D("4"))
        inventario().registrar_entrada("COMPRA", "COMPRA", 1, [linea], actor.usuario_id, HOY)
    bar = Cliente.objects.create(nombre="Bar El Lúpulo", tipo_doc="RUC", num_doc="20512345671")
    return actor, ids, bar.id


def datos(v, *lineas, fecha=date(2026, 11, 15)):
    _, ids, cliente = v
    filas = tuple(LineaPedido(ids[sku], D(q), D(precio)) for sku, q, precio in lineas)
    return uc.DatosPedido(cliente, fecha, "Para el viernes", filas)


def crear(v, *lineas):
    return caso_de_pedido(uc.CrearPedido).ejecutar(v[0], datos(v, *lineas))


def test_crear_editar_y_aprobar(v):
    """RF-VEN-06, RF-VEN-07 (editar un Creado), RF-VEN-08 y RF-VEN-48."""
    actor, _, _ = v
    id_ = crear(v, ("TER-IPA-330", "24", "12"))
    p = Pedido.objects.get(pk=id_)
    assert (p.numero, p.estado, p.total) == (1, "CREADO", D("288.00"))
    caso_de_pedido(uc.EditarPedido).ejecutar(actor, id_, datos(v, ("TER-IPA-330", "30", "12")))
    caso_de_pedido(uc.AprobarPedido).ejecutar(actor, id_, HOY)
    p.refresh_from_db()
    assert (p.estado, p.total, p.aprobado_por_id) == ("APROBADO", D("360.00"), actor.usuario_id)


def test_aprobar_exige_stock_e_informa_todos_los_faltantes(v):
    """RF-VEN-08 (doble validación, art. 10.3)."""
    id_ = crear(v, ("TER-IPA-330", "60", "12"), ("TER-IPA-20L", "2", "380"))
    with pytest.raises(
        PedidoInvalido,
        match="Stock insuficiente: TER-IPA-330 faltan 12.0000; TER-IPA-20L faltan 2.0000",
    ):
        caso_de_pedido(uc.AprobarPedido).ejecutar(v[0], id_, HOY)
    assert Pedido.objects.get(pk=id_).estado == "CREADO"


def test_aprobado_solo_cambia_fecha_y_comentario(v):
    """RF-VEN-11."""
    actor = v[0]
    id_ = crear(v, ("TER-IPA-330", "24", "12"))
    caso_de_pedido(uc.AprobarPedido).ejecutar(actor, id_, HOY)
    with pytest.raises(PedidoInvalido, match="El pedido está aprobado: cancélalo y crea otro"):
        caso_de_pedido(uc.EditarPedido).ejecutar(actor, id_, datos(v, ("TER-IPA-330", "30", "12")))
    nueva = datos(v, ("TER-IPA-330", "24", "12"), fecha=date(2026, 11, 20))
    caso_de_pedido(uc.EditarPedido).ejecutar(actor, id_, nueva)
    assert Pedido.objects.get(pk=id_).fecha_entrega == date(2026, 11, 20)


@pytest.mark.parametrize(
    "lineas, mensaje",
    [
        ((("TER-IPA-330", "1", "12"), ("TER-IPA-330", "2", "12")), "Un producto está repetido"),
        ((("TER-IPA-330", "0", "12"),), "La cantidad debe ser mayor a 0"),
    ],
)
def test_lineas_invalidas(v, lineas, mensaje):
    with pytest.raises(PedidoInvalido, match=mensaje):
        crear(v, *lineas)


def test_cliente_inactivo_y_producto_que_no_se_vende(v):
    """RF-VEN-44 y producto vendible."""
    actor, ids, cliente = v
    Producto.objects.filter(pk=ids["TER-IPA-20L"]).update(se_vende=False, precio_venta=None)
    with pytest.raises(PedidoInvalido, match="TER-IPA-20L no se vende o está inactivo"):
        crear(v, ("TER-IPA-20L", "1", "380"))
    Cliente.objects.filter(pk=cliente).update(activo=False)
    with pytest.raises(PedidoInvalido, match="El cliente no existe o está inactivo"):
        crear(v, ("TER-IPA-330", "1", "12"))


def test_cancelar_con_motivo_y_permiso(v):
    """RF-VEN-37."""
    actor = v[0]
    id_ = crear(v, ("TER-IPA-330", "24", "12"))
    sin = Actor(actor.usuario_id, actor.empresa_id, actor.permisos - {uc.CANCELAR})
    with pytest.raises(AccesoDenegado):
        caso_de_pedido(uc.CancelarPedido).ejecutar(sin, id_, "x")
    with pytest.raises(PedidoInvalido, match="Indica el motivo"):
        caso_de_pedido(uc.CancelarPedido).ejecutar(actor, id_, " ")
    caso_de_pedido(uc.CancelarPedido).ejecutar(actor, id_, "El cliente desistió")
    p = Pedido.objects.get(pk=id_)
    assert (p.estado, p.motivo_cancelacion) == ("CANCELADO", "El cliente desistió")
    with pytest.raises(PedidoInvalido, match="El pedido está cancelado"):
        caso_de_pedido(uc.AprobarPedido).ejecutar(actor, id_, HOY)
