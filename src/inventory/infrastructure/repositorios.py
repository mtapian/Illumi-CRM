"""Adaptador de PostgreSQL del inventario (plan 0003a §2). Los locks siguen el orden del
plan 0000 §5: primero `costo_producto` (mutex por producto), después el stock."""

from decimal import Decimal

from django.db.models import F, Sum

from inventory.domain.costo import CostoProducto as Costo
from inventory.domain.existencia import Existencia
from inventory.domain.existencia import Movimiento as Mov
from inventory.infrastructure.models import Almacen, CostoProducto, Lote, Movimiento, Stock
from shared.domain.tenant import empresa_actual


def _mov(m) -> Mov:
    return Mov(
        m.id,
        m.tipo,
        m.cantidad,
        m.costo_unitario,
        m.almacen_id,
        m.lote_id,
        m.revierte_id,
        m.producto_id,
    )


class InventarioOrm:
    def bloquear(self, producto_ids):
        CostoProducto.objects.bulk_create(
            [CostoProducto(empresa_id=empresa_actual(), producto_id=p) for p in producto_ids],
            ignore_conflicts=True,
        )
        list(
            CostoProducto.objects.select_for_update()
            .filter(producto_id__in=producto_ids)
            .order_by("producto_id")
        )

    def costo(self, producto_id):
        c = CostoProducto.objects.get(producto_id=producto_id)
        return Costo(c.cantidad_total, c.valor_total, c.costo_promedio)

    def guardar_costo(self, producto_id, costo):
        CostoProducto.objects.filter(producto_id=producto_id).update(
            cantidad_total=costo.cantidad, valor_total=costo.valor, costo_promedio=costo.promedio
        )

    def almacen(self, almacen_id):
        return Almacen.objects.filter(pk=almacen_id).values_list("nombre", flat=True).first()

    def existencias(self, producto_id, almacen_id):
        filas = (
            Stock.objects.select_for_update(of=("self",))
            .select_related("lote")
            .filter(producto_id=producto_id, almacen_id=almacen_id)
            .order_by("lote_id", "id")
        )
        return [
            Existencia(
                s.cantidad,
                s.lote.codigo if s.lote else None,
                s.lote.fecha_vencimiento if s.lote else None,
                s.lote.fecha_ingreso if s.lote else None,
                s.id,
                lote_id=s.lote_id,
            )
            for s in filas
        ]

    def lote(self, producto_id, codigo):
        fila = Lote.objects.filter(producto_id=producto_id, codigo=codigo)
        return fila.values_list("id", "fecha_vencimiento").first()

    def crear_lote(self, producto_id, codigo, ingreso, vencimiento, origen):
        return Lote.objects.create(
            producto_id=producto_id,
            codigo=codigo,
            fecha_ingreso=ingreso,
            fecha_vencimiento=vencimiento,
            origen_tipo=origen[0],
            origen_id=origen[1],
        ).id

    def sumar_stock(self, producto_id, almacen_id, lote_id, cantidad):
        fila, _ = Stock.objects.get_or_create(
            producto_id=producto_id, almacen_id=almacen_id, lote_id=lote_id
        )
        Stock.objects.filter(pk=fila.pk).update(cantidad=F("cantidad") + cantidad)

    def fijar_stock(self, stock_id, cantidad):
        Stock.objects.filter(pk=stock_id).update(cantidad=cantidad)

    def insertar_movimiento(self, **campos):
        return Movimiento.objects.create(**campos).id

    def por_revertir(self, ref_tipo, ref_id):
        filas = Movimiento.objects.filter(
            ref_tipo=ref_tipo, ref_id=ref_id, revierte__isnull=True
        ).exclude(pk__in=Movimiento.objects.filter(revierte__isnull=False).values("revierte_id"))
        return [_mov(m) for m in filas.order_by("id")]

    def movimientos(self, producto_id):
        return [_mov(m) for m in Movimiento.objects.filter(producto_id=producto_id).order_by("id")]


class InventarioConsulta:
    """Implementa el puerto del catálogo `InventarioConsultaPort` (plan 0003a §1)."""

    def stock(self, producto_id: int) -> Decimal:
        total = Stock.objects.filter(producto_id=producto_id).aggregate(t=Sum("cantidad"))["t"]
        return total or Decimal("0")

    def tiene_movimientos(self, producto_id: int) -> bool:
        return Movimiento.objects.filter(producto_id=producto_id).exists()
