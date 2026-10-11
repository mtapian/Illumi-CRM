"""Consultas de lectura del inventario (plan 0003c §1): stock, kardex y alertas. No cambian
stock; usan el ORM con los índices de §2."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from catalog.infrastructure.models import Producto
from inventory.domain.alertas import bajo_minimo
from inventory.domain.costo import importe
from inventory.domain.lotes import dias_restantes, lote_vencido, por_vencer
from inventory.infrastructure.models import ConfigInventario, CostoProducto, Movimiento, Stock

CASILLAS = ("se_compra", "se_fabrica", "se_vende")
SIN_CATEGORIA = "Sin categoría"
CERO = Decimal("0")


def dias_alerta() -> int:
    fila = ConfigInventario.objects.values_list("dias_alerta_vencimiento", flat=True).first()
    return fila or 30


@dataclass
class FilaStock:
    producto: Producto
    cantidad: Decimal
    promedio: Decimal
    valor: Decimal
    detalle: list = field(default_factory=list)  # [(almacén, lote, vencimiento, cantidad)]


def stock(filtros: dict) -> tuple[list[FilaStock], dict[str, Decimal], Decimal]:
    """RF-INV-04 y 05: filas por producto, valorización por categoría y total general. Con
    filtro de almacén, cantidad y valor son de ese almacén (valor = cantidad × promedio)."""
    productos = Producto.objects.filter(tipo="BIEN", activo=True).select_related(
        "unidad", "categoria"
    )
    if q := filtros.get("q", "").strip():
        productos = productos.filter(Q(sku__icontains=q) | Q(nombre__icontains=q))
    if filtros.get("casilla") in CASILLAS:
        productos = productos.filter(**{filtros["casilla"]: True})
    if filtros.get("categoria", "").isdigit():
        productos = productos.filter(categoria_id=filtros["categoria"])
    existencias = Stock.objects.filter(cantidad__gt=0).select_related("almacen", "lote")
    almacen = filtros.get("almacen", "")
    if almacen.isdigit():
        existencias = existencias.filter(almacen_id=almacen)
    detalle = defaultdict(list)
    for s in existencias.order_by("almacen__nombre", "lote__fecha_vencimiento", "lote_id"):
        lote = s.lote
        detalle[s.producto_id].append(
            (s.almacen.nombre, lote and lote.codigo, lote and lote.fecha_vencimiento, s.cantidad)
        )
    costos = {c.producto_id: c for c in CostoProducto.objects.filter(producto__in=productos)}
    filas, por_categoria = [], defaultdict(Decimal)
    for p in productos.order_by("nombre"):
        cantidad = sum((d[3] for d in detalle[p.id]), CERO)
        costo = costos.get(p.id)
        promedio = costo.costo_promedio if costo else CERO
        por_almacen = almacen.isdigit() or not costo
        valor = importe(cantidad * promedio) if por_almacen else costo.valor_total
        if filtros.get("con_stock") and cantidad <= 0:
            continue
        if filtros.get("stock_bajo") and not bajo_minimo(cantidad, p.stock_minimo):
            continue
        filas.append(FilaStock(p, cantidad, promedio, valor, detalle[p.id]))
        por_categoria[p.categoria.nombre if p.categoria else SIN_CATEGORIA] += valor
    return filas, dict(sorted(por_categoria.items())), sum(por_categoria.values(), CERO)


def kardex(filtros: dict, despues: int | None = None, limite: int | None = 50):
    """RF-INV-06 y 07: movimientos filtrados, en orden, paginados por cursor (`id`)."""
    movs = Movimiento.objects.select_related("producto", "almacen", "lote", "usuario")
    for campo in ("producto", "almacen"):
        if filtros.get(campo, "").isdigit():
            movs = movs.filter(**{f"{campo}_id": filtros[campo]})
    if lote := filtros.get("lote", "").strip():
        movs = movs.filter(lote__codigo=lote)
    if motivo := filtros.get("motivo", "").strip():
        movs = movs.filter(motivo=motivo)
    if filtros.get("desde"):
        movs = movs.filter(fecha__date__gte=filtros["desde"])  # hora de Lima (TIME_ZONE)
    if filtros.get("hasta"):
        movs = movs.filter(fecha__date__lte=filtros["hasta"])
    if despues:
        movs = movs.filter(id__gt=despues)
    movs = movs.order_by("id")
    return list(movs[:limite]) if limite else movs


def bajo_minimo_productos() -> list[tuple[Producto, Decimal]]:
    """RF-INV-14: productos con stock mínimo > 0 y stock total ≤ mínimo."""
    productos = Producto.objects.filter(tipo="BIEN", activo=True, stock_minimo__gt=0)
    totales = dict(
        Stock.objects.filter(producto__in=productos)
        .values("producto_id")
        .annotate(t=Sum("cantidad"))
        .values_list("producto_id", "t")
    )
    filas = [(p, totales.get(p.id, CERO)) for p in productos.order_by("nombre")]
    return [(p, total) for p, total in filas if bajo_minimo(total, p.stock_minimo)]


def lotes_en_alerta(hoy: date) -> list[dict]:
    """RF-INV-15 y 16: lotes con stock vencidos o por vencer dentro de los días de alerta."""
    dias = dias_alerta()
    filas = (
        Stock.objects.filter(cantidad__gt=0, lote__fecha_vencimiento__isnull=False)
        .values("lote__codigo", "lote__fecha_vencimiento", "producto__sku", "producto__nombre")
        .annotate(cantidad=Sum("cantidad"))
        .order_by("lote__fecha_vencimiento", "lote__codigo")
    )
    alertas = []
    for f in filas:
        vence = f["lote__fecha_vencimiento"]
        vencido = lote_vencido(vence, hoy)
        if vencido or por_vencer(vence, dias, hoy):
            alertas.append(
                {
                    "lote": f["lote__codigo"],
                    "sku": f["producto__sku"],
                    "nombre": f["producto__nombre"],
                    "cantidad": f["cantidad"],
                    "vence": vence,
                    "vencido": vencido,
                    "dias": dias_restantes(vence, hoy),
                }
            )
    return alertas
