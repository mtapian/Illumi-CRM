"""Consultas agregadas del inicio (spec 0008c, RF-FIN-14, 18 a 23).

Una consulta por cifra, en la base (RNF-FIN-04). Venta = pedido Facturado o Entregado por su
fecha de emisión, con su total con impuestos (PO, Q1 y Q2). Se llaman dentro del contexto de
la empresa.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import ExtractMonth

from sales.domain.pedido import ENTREGADO, FACTURADO
from sales.infrastructure.models import Pago, Pedido, PedidoLinea

CERO = Decimal("0")
SIN_CATEGORIA = "Sin categoría"


def _ventas(desde: date, hasta: date):
    return Pedido.objects.filter(
        estado__in=(FACTURADO, ENTREGADO), fecha_emision__gte=desde, fecha_emision__lte=hasta
    )


def ventas_entre(desde: date, hasta: date) -> Decimal:
    """RF-FIN-14: ventas de hoy (desde = hasta) o del mes."""
    return _ventas(desde, hasta).aggregate(t=Sum("total"))["t"] or CERO


def ventas_por_dia(hasta: date, dias: int = 14) -> list[tuple[date, Decimal]]:
    """RF-FIN-18: un valor por día, con 0 los días sin ventas."""
    desde = hasta - timedelta(days=dias - 1)
    por_dia = dict(
        _ventas(desde, hasta).values_list("fecha_emision").annotate(t=Sum("total")).order_by()
    )
    return [(d, por_dia.get(d, CERO)) for d in (desde + timedelta(n) for n in range(dias))]


def ventas_por_mes(anio: int) -> list[tuple[int, Decimal]]:
    """RF-FIN-19: los 12 meses del año."""
    filas = (
        _ventas(date(anio, 1, 1), date(anio, 12, 31))
        .annotate(mes=ExtractMonth("fecha_emision"))
        .values_list("mes")
        .annotate(t=Sum("total"))
        .order_by()
    )
    por_mes = dict(filas)
    return [(m, por_mes.get(m, CERO)) for m in range(1, 13)]


def cobrado_por_metodo(desde: date, hasta: date) -> list[tuple[str, Decimal]]:
    """RF-FIN-20: pagos vigentes por su fecha, de mayor a menor."""
    filas = (
        Pago.objects.filter(anulado_en__isnull=True, fecha__gte=desde, fecha__lte=hasta)
        .values_list("metodo__nombre")
        .annotate(t=Sum("monto"))
        .order_by("-t", "metodo__nombre")
    )
    return list(filas)


def _lineas(desde: date, hasta: date):
    return PedidoLinea.objects.filter(
        pedido__estado__in=(FACTURADO, ENTREGADO),
        pedido__fecha_emision__gte=desde,
        pedido__fecha_emision__lte=hasta,
    )


def ventas_por_categoria(desde: date, hasta: date) -> list[tuple[str, Decimal]]:
    """RF-FIN-21: total de las líneas por categoría del producto, de mayor a menor."""
    filas = (
        _lineas(desde, hasta)
        .values_list("producto__categoria__nombre")
        .annotate(t=Sum("subtotal"))
        .order_by("-t")
    )
    return [(nombre or SIN_CATEGORIA, total) for nombre, total in filas]


def mas_vendidos(desde: date, hasta: date, n: int = 5) -> list[tuple[str, str, Decimal, Decimal]]:
    """RF-FIN-22: (SKU, nombre, unidades, total) de los n de mayor total."""
    filas = (
        _lineas(desde, hasta)
        .values_list("producto__sku", "producto__nombre")
        .annotate(unidades=Sum("cantidad"), total=Sum("subtotal"))
        .order_by("-total", "producto__sku")
    )
    return list(filas[:n])


def ultimas_ventas(n: int = 6) -> list[Pedido]:
    """RF-FIN-23: las más recientes por fecha y hora de facturación."""
    filas = Pedido.objects.filter(estado__in=(FACTURADO, ENTREGADO)).select_related("cliente")
    return list(filas.order_by("-facturado_en", "-numero")[:n])
