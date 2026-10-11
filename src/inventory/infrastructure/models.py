"""Modelos del inventario (plan 0003a §2). La base refuerza las reglas del dominio:
stock y valor sin negativos, movimientos inmutables y una sola reversión por movimiento."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from shared.infrastructure.tenant_models import TenantModel


def _cantidad(**kw):
    return models.DecimalField(max_digits=14, decimal_places=4, **kw)


def _importe(**kw):
    return models.DecimalField(max_digits=14, decimal_places=2, **kw)


def _costo(**kw):
    return models.DecimalField(max_digits=14, decimal_places=6, **kw)


class Almacen(TenantModel):
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint("empresa", Lower("nombre"), name="almacen_unico_sin_mayusculas")
        ]

    def __str__(self):
        return self.nombre


class Lote(TenantModel):
    """Lote de cualquier bien, registrado en un ingreso o en una OP (RF-CAT-40, RF-INV-26)."""

    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    codigo = models.CharField(max_length=40)
    fecha_ingreso = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    origen_tipo = models.CharField(max_length=10, blank=True)  # COMPRA, AJUSTE, OP
    origen_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "producto", "codigo"], name="lote_unico")
        ]


class Stock(TenantModel):
    """Existencia por producto × almacén × lote; `lote` nulo es el stock sin lote."""

    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="stock")
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, related_name="+")
    cantidad = _cantidad(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "producto", "almacen", "lote"],
                name="stock_unico",
                nulls_distinct=False,
            ),
            models.CheckConstraint(condition=Q(cantidad__gte=0), name="stock_no_negativo"),
        ]


class CostoProducto(TenantModel):
    """Cantidad y valor totales del producto; el promedio es valor / cantidad (RF-INV-18)."""

    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    cantidad_total = _cantidad(default=0)
    valor_total = _importe(default=0)
    costo_promedio = _costo(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "producto"], name="costo_por_producto"),
            models.CheckConstraint(
                condition=Q(cantidad_total__gte=0, valor_total__gte=0)
                & (Q(cantidad_total__gt=0) | Q(valor_total=0)),  # RF-INV-24
                name="costo_no_negativo_y_cero_vale_cero",
            ),
        ]


class Movimiento(TenantModel):
    """Cada entrada o salida, con su costo y saldo; no se edita ni se borra (RF-INV-17)."""

    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=7, choices=[("ENTRADA", "Entrada"), ("SALIDA", "Salida")])
    motivo = models.CharField(max_length=20)
    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="+")
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, related_name="+")
    cantidad = _cantidad()
    costo_unitario = _costo()
    costo_total = _importe()
    saldo_cantidad = _cantidad()
    saldo_promedio = _costo()
    ref_tipo = models.CharField(max_length=10)  # COMPRA, AJUSTE, OP, VENTA
    ref_id = models.BigIntegerField(null=True)
    revierte = models.ForeignKey("self", on_delete=models.PROTECT, null=True, related_name="+")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(  # RF-INV-20: un movimiento se revierte una sola vez
                fields=["revierte"], condition=Q(revierte__isnull=False), name="revierte_una_vez"
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gt=0, costo_unitario__gte=0, costo_total__gte=0)
                & Q(saldo_cantidad__gte=0),
                name="movimiento_valores_validos",
            ),
        ]
