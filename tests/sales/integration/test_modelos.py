"""0006a, T4: la base refuerza las reglas de clientes y pedidos (RF-VEN-01, 03, 05, 06, 11)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from catalog.infrastructure.models import Producto
from sales.infrastructure.models import Cliente, Pedido, PedidoLinea

pytestmark = pytest.mark.django_db
HOY = date(2026, 11, 10)


def falla(excepcion, crear):
    with transaction.atomic(), pytest.raises(excepcion):
        crear()


def test_clientes_varios_y_documento_unico(empresa_ventas):
    """RF-VEN-03 y 01: un solo genérico, siempre activo; documento único salvo sin número."""
    generico = Cliente.objects.get(es_generico=True)
    assert (generico.nombre, generico.tipo_doc, generico.num_doc) == ("Clientes varios", "SD", "")
    falla(
        IntegrityError,
        lambda: Cliente.objects.create(nombre="Otro", tipo_doc="SD", es_generico=True),
    )
    falla(IntegrityError, lambda: Cliente.objects.filter(pk=generico.pk).update(activo=False))
    Cliente.objects.create(nombre="Turista", tipo_doc="SD")  # sin número: no choca
    Cliente.objects.create(nombre="Bar", tipo_doc="RUC", num_doc="20512345671")
    falla(
        IntegrityError,
        lambda: Cliente.objects.create(nombre="X", tipo_doc="RUC", num_doc="20512345671"),
    )


def test_pedido_y_lineas(empresa_ventas):
    """RF-VEN-06, 11, 37: número único, cancelado con motivo, líneas válidas y fijas al aprobar."""
    _, actor = empresa_ventas
    cliente = Cliente.objects.get(es_generico=True)
    ipa = Producto.objects.get(sku="TER-IPA-330")

    def pedido(numero, **kw):
        return Pedido.objects.create(numero=numero, cliente=cliente, fecha_entrega=HOY, **kw)

    p = pedido(1)
    falla(IntegrityError, lambda: pedido(1))
    falla(IntegrityError, lambda: pedido(2, estado="CANCELADO"))
    falla(IntegrityError, lambda: pedido(3, estado="OTRO"))

    def linea(cantidad="1", precio="12"):
        return PedidoLinea.objects.create(
            pedido=p, producto=ipa, cantidad=D(cantidad), precio=D(precio), subtotal=D("0")
        )

    falla(IntegrityError, lambda: linea(cantidad="0"))
    falla(IntegrityError, lambda: linea(precio="0"))
    x = linea()
    falla(IntegrityError, lambda: linea())  # un producto, una línea
    Pedido.objects.filter(pk=p.pk).update(estado="APROBADO")
    with transaction.atomic(), pytest.raises(DatabaseError):
        PedidoLinea.objects.filter(pk=x.pk).update(cantidad=D("2"))
