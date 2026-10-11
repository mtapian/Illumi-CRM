"""Adaptadores de PostgreSQL de proveedores y compras (planes 0002d y 0004a §2)."""

from dataclasses import asdict

from django.utils import timezone

from inventory.infrastructure.models import Almacen
from purchasing.application.compras import DatosCompra, Totales
from purchasing.domain.compra import ANULADA, FINALIZADA, LineaCompra, subtotal_linea
from purchasing.domain.proveedor import DatosProveedor
from purchasing.infrastructure.models import Compra, CompraLinea, Proveedor, ProveedorProducto
from shared.domain.tenant import empresa_actual


class ProveedoresOrm:
    def activo(self, proveedor_id):
        return Proveedor.objects.filter(pk=proveedor_id).values_list("activo", flat=True).first()

    def existe_documento(self, tipo, numero, excluir):
        filas = Proveedor.objects.filter(tipo_doc=tipo, num_doc=numero)
        return filas.exclude(pk=excluir).exists()

    def guardar(self, proveedor_id, datos: DatosProveedor):
        if proveedor_id is None:
            return Proveedor.objects.create(**asdict(datos)).id
        Proveedor.objects.filter(pk=proveedor_id).update(**asdict(datos))
        return proveedor_id

    def cambiar_estado(self, proveedor_id, activo):
        Proveedor.objects.filter(pk=proveedor_id).update(activo=activo)

    def eliminar(self, proveedor_id):
        Proveedor.objects.filter(pk=proveedor_id).delete()

    def asociar(self, proveedor_id, producto_id, precio, plazo, codigo):
        ProveedorProducto.objects.update_or_create(
            proveedor_id=proveedor_id,
            producto_id=producto_id,
            defaults={
                "precio_referencial": precio,
                "plazo_entrega_dias": plazo,
                "codigo_proveedor": codigo,
            },
        )

    def quitar(self, proveedor_id, producto_id):
        ProveedorProducto.objects.filter(
            proveedor_id=proveedor_id, producto_id=producto_id
        ).delete()


class ComprasOrm:
    def proveedor(self, proveedor_id):
        fila = Proveedor.objects.filter(pk=proveedor_id)
        return fila.values_list("activo", "tipo_doc", "razon_social").first()

    def almacen_activo(self, almacen_id):
        return Almacen.objects.filter(pk=almacen_id).values_list("activo", flat=True).first()

    def con_documento(self, proveedor_id, doc_tipo, serie, excluir):
        filas = Compra.objects.filter(
            proveedor_id=proveedor_id, doc_tipo=doc_tipo, doc_serie_numero=serie
        ).exclude(estado=ANULADA)
        return filas.exclude(pk=excluir).values_list("numero", flat=True).first()

    def _cabecera(self, datos: DatosCompra, t: Totales) -> dict:
        campos = asdict(t) | asdict(datos)
        del campos["lineas"]
        return campos

    def _lineas(self, compra_id, lineas: list[LineaCompra]):
        CompraLinea.objects.bulk_create(
            CompraLinea(
                empresa_id=empresa_actual(),  # bulk_create no pasa por save()
                compra_id=compra_id,
                producto_id=x.producto_id,
                cantidad=x.cantidad,
                costo_unitario=x.costo_unitario,
                es_bonificacion=x.bonificacion,
                subtotal=subtotal_linea(x),
                lote_codigo=x.lote or "",
                vencimiento=x.vencimiento,
            )
            for x in lineas
        )

    def crear(self, numero, datos, t, usuario_id):
        compra = Compra.objects.create(
            numero=numero, usuario_id=usuario_id, **self._cabecera(datos, t)
        )
        self._lineas(compra.id, datos.lineas)
        return compra.id

    def actualizar(self, compra_id, datos, t):
        Compra.objects.filter(pk=compra_id).update(**self._cabecera(datos, t))
        CompraLinea.objects.filter(compra_id=compra_id).delete()
        self._lineas(compra_id, datos.lineas)

    def bloquear(self, compra_id):
        c = Compra.objects.select_for_update().filter(pk=compra_id).first()
        if c is None:
            return None
        lineas = [
            LineaCompra(
                x.producto_id,
                x.cantidad,
                x.costo_unitario,
                x.es_bonificacion,
                x.lote_codigo or None,
                x.vencimiento,
            )
            for x in c.lineas.order_by("id")
        ]
        datos = DatosCompra(
            c.proveedor_id,
            c.fecha,
            c.almacen_id,
            c.doc_tipo,
            c.doc_serie_numero,
            c.observacion,
            lineas,
        )
        return c.estado, datos

    def cambiar_estado(self, compra_id, estado):
        Compra.objects.filter(pk=compra_id).update(estado=estado)

    def finalizar(self, compra_id, almacen_id, recepcion, guia, usuario_id):
        Compra.objects.filter(pk=compra_id).update(
            estado=FINALIZADA,
            almacen_id=almacen_id,
            fecha_recepcion=recepcion,
            guia_remision=guia,
            finalizada_por_id=usuario_id,
            finalizada_en=timezone.now(),
        )

    def tiene_compras(self, proveedor_id):
        """RF-COM-24: una compra no anulada, en cualquier estado."""
        return Compra.objects.filter(proveedor_id=proveedor_id).exclude(estado=ANULADA).exists()
