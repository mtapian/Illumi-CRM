"""Persistencia de ventas (plan 0006a §2)."""

from dataclasses import fields

from django.shortcuts import get_object_or_404
from django.utils import timezone

from sales.application.pedidos import DatosPedido
from sales.domain.cliente import DatosCliente
from sales.domain.pedido import APROBADO, CANCELADO, LineaPedido, subtotal
from sales.infrastructure.models import Cliente, Pedido, PedidoLinea
from shared.domain.tenant import empresa_actual

_CAMPOS = [f.name for f in fields(DatosCliente)]


class ClientesOrm:
    def cliente(self, cliente_id):
        c = Cliente.objects.filter(pk=cliente_id).first()
        if c is None:
            return None
        return DatosCliente(**{f: getattr(c, f) for f in _CAMPOS}), c.es_generico

    def existe_documento(self, tipo, numero, excluir):
        filas = Cliente.objects.filter(tipo_doc=tipo, num_doc=numero)
        return filas.exclude(pk=excluir).exists() if excluir else filas.exists()

    def guardar(self, cliente_id, datos) -> int:
        valores = {f: getattr(datos, f) for f in _CAMPOS}
        if cliente_id is None:
            return Cliente.objects.create(**valores).id
        Cliente.objects.filter(pk=cliente_id).update(**valores)
        return cliente_id

    def cambiar_estado(self, cliente_id, activo) -> None:
        Cliente.objects.filter(pk=cliente_id).update(activo=activo)


def _datos(p: Pedido) -> DatosPedido:
    return DatosPedido(
        p.cliente_id,
        p.fecha_entrega,
        p.comentario,
        tuple(LineaPedido(x.producto_id, x.cantidad, x.precio) for x in p.lineas.order_by("id")),
    )


class PedidosOrm:
    def cliente_activo(self, cliente_id) -> bool:
        return Cliente.objects.filter(pk=cliente_id, activo=True).exists()

    def _lineas(self, pedido_id, lineas) -> None:
        PedidoLinea.objects.filter(pedido_id=pedido_id).delete()
        PedidoLinea.objects.bulk_create(
            PedidoLinea(
                empresa_id=empresa_actual(),
                pedido_id=pedido_id,
                producto_id=x.producto_id,
                cantidad=x.cantidad,
                precio=x.precio,
                subtotal=subtotal(x),
            )
            for x in lineas
        )

    def crear(self, numero, datos, total, usuario_id) -> int:
        p = Pedido.objects.create(
            numero=numero,
            cliente_id=datos.cliente_id,
            fecha_entrega=datos.fecha_entrega,
            comentario=datos.comentario,
            total=total,
            creado_por_id=usuario_id,
        )
        self._lineas(p.id, datos.lineas)
        return p.id

    def actualizar(self, pedido_id, datos, total, lineas) -> None:
        Pedido.objects.filter(pk=pedido_id).update(
            cliente_id=datos.cliente_id,
            fecha_entrega=datos.fecha_entrega,
            comentario=datos.comentario,
            total=total,
        )
        if lineas:
            self._lineas(pedido_id, datos.lineas)

    def bloquear(self, pedido_id):
        p = get_object_or_404(Pedido.objects.select_for_update(of=("self",)), pk=pedido_id)
        return p.estado, _datos(p)

    def aprobar(self, pedido_id, usuario_id) -> None:
        Pedido.objects.filter(pk=pedido_id).update(
            estado=APROBADO, aprobado_por_id=usuario_id, aprobado_en=timezone.now()
        )

    def cancelar(self, pedido_id, usuario_id, motivo) -> None:
        Pedido.objects.filter(pk=pedido_id).update(
            estado=CANCELADO,
            cancelado_por_id=usuario_id,
            cancelado_en=timezone.now(),
            motivo_cancelacion=motivo,
        )
