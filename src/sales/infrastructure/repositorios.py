"""Persistencia de ventas (plan 0006a §2)."""

from dataclasses import fields

from django.shortcuts import get_object_or_404
from django.utils import timezone

from sales.application.pedidos import DatosPedido
from sales.domain.cliente import DatosCliente
from sales.domain.pedido import (
    APROBADO,
    CANCELADO,
    ENTREGADO,
    FACTURADO,
    LineaPedido,
    subtotal,
)
from sales.infrastructure.models import (
    Cliente,
    Cobranza,
    Cuota,
    MetodoPago,
    Pago,
    Pedido,
    PedidoLinea,
)
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

    def crear(self, numero, datos, total, usuario_id, token=None) -> int:
        p = Pedido.objects.create(
            numero=numero,
            token=token,
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


class FacturasOrm(PedidosOrm):
    """Facturar y entregar (0006b): el pedido facturado lleva el desglose y la cobranza."""

    def cliente(self, cliente_id):
        c = Cliente.objects.get(pk=cliente_id)
        return c.tipo_doc, c.es_generico, c.activo

    def facturar(
        self, pedido_id, comprobante, forma_pago, almacen_id, emision, lineas, usuario_id
    ) -> None:
        for x in lineas:  # con el pedido aún Aprobado (trigger de líneas)
            PedidoLinea.objects.filter(pedido_id=pedido_id, producto_id=x.producto_id).update(
                valor=x.valor, isc=x.isc, igv=x.igv, costo=x.costo
            )
        Pedido.objects.filter(pk=pedido_id).update(
            estado=FACTURADO,
            comprobante=comprobante,
            forma_pago=forma_pago,
            almacen_id=almacen_id,
            fecha_emision=emision,
            costo_total=sum(x.costo for x in lineas),
            facturado_por_id=usuario_id,
            facturado_en=timezone.now(),
        )

    def crear_cobranza(self, pedido_id, cliente_id, total, emision, cuotas) -> int:
        c = Cobranza.objects.create(
            pedido_id=pedido_id, cliente_id=cliente_id, emision=emision, total=total
        )
        Cuota.objects.bulk_create(
            Cuota(
                empresa_id=empresa_actual(),
                cobranza=c,
                numero=n,
                monto=x.monto,
                vencimiento=x.vencimiento,
            )
            for n, x in enumerate(cuotas, 1)
        )
        return c.id

    def por_token(self, token) -> int | None:
        return Pedido.objects.filter(token=token).values_list("id", flat=True).first()

    def cobranza_de(self, pedido_id) -> int:
        return Cobranza.objects.get(pedido_id=pedido_id).id

    def entregar(self, pedido_id, usuario_id) -> None:
        Pedido.objects.filter(pk=pedido_id).update(
            estado=ENTREGADO, entregado_por_id=usuario_id, entregado_en=timezone.now()
        )


class CobranzasOrm:
    """Pagos y métodos de pago (0006b)."""

    def bloquear(self, cobranza_id):
        c = get_object_or_404(Cobranza.objects.select_for_update(), pk=cobranza_id)
        return c.estado, c.total, c.pagado

    def metodo_activo(self, metodo_id) -> bool:
        return MetodoPago.objects.filter(pk=metodo_id, activo=True).exists()

    def registrar_pago(self, cobranza_id, datos, usuario_id) -> int:
        return Pago.objects.create(
            cobranza_id=cobranza_id,
            metodo_id=datos.metodo_id,
            monto=datos.monto,
            fecha=datos.fecha,
            referencia=datos.referencia,
            registrado_por_id=usuario_id,
        ).id

    def actualizar(self, cobranza_id, pagado, estado) -> None:
        Cobranza.objects.filter(pk=cobranza_id).update(pagado=pagado, estado=estado)

    def pago(self, pago_id):
        p = get_object_or_404(Pago, pk=pago_id)
        return p.cobranza_id, p.monto, p.anulado_en is not None

    def anular_pago(self, pago_id, usuario_id, motivo) -> None:
        Pago.objects.filter(pk=pago_id).update(
            anulado_por_id=usuario_id, anulado_en=timezone.now(), motivo_anulacion=motivo
        )

    def existe_metodo(self, nombre, excluir) -> bool:
        return MetodoPago.objects.filter(nombre__iexact=nombre).exclude(pk=excluir).exists()

    def guardar_metodo(self, metodo_id, nombre) -> int:
        if metodo_id is None:
            return MetodoPago.objects.create(nombre=nombre).id
        get_object_or_404(MetodoPago, pk=metodo_id)
        MetodoPago.objects.filter(pk=metodo_id).update(nombre=nombre)
        return metodo_id

    def estado_metodo(self, metodo_id, activo) -> None:
        get_object_or_404(MetodoPago, pk=metodo_id)
        MetodoPago.objects.filter(pk=metodo_id).update(activo=activo)
