"""Modelos de compras (planes 0002d y 0004a §2). La base refuerza las reglas del dominio."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from shared.infrastructure.tenant_models import TenantModel


class Proveedor(TenantModel):
    tipo_doc = models.CharField(max_length=3, choices=[("RUC", "RUC"), ("DNI", "DNI")])
    num_doc = models.CharField(max_length=11)
    razon_social = models.CharField(max_length=200)
    contacto = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    email = models.CharField(max_length=120, blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # RF-COM-01: el mismo documento puede estar en otra empresa, no dos veces en la misma.
            models.UniqueConstraint(
                fields=["empresa", "tipo_doc", "num_doc"], name="proveedor_documento_unico"
            )
        ]

    def __str__(self):
        return self.razon_social


class ProveedorProducto(TenantModel):
    """Proveedor habitual de un producto comprable (RF-COM-21). No es el costo."""

    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="productos")
    producto = models.ForeignKey("catalog.Producto", on_delete=models.CASCADE, related_name="+")
    precio_referencial = models.DecimalField(max_digits=14, decimal_places=2)
    plazo_entrega_dias = models.IntegerField()
    codigo_proveedor = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["proveedor", "producto"], name="proveedor_producto_unico"
            ),
            models.CheckConstraint(
                condition=Q(precio_referencial__gte=0) & Q(plazo_entrega_dias__gte=0),
                name="proveedor_producto_no_negativos",
            ),
        ]


def _decimal(decimales, **kw):
    return models.DecimalField(max_digits=14, decimal_places=decimales, **kw)


class Compra(TenantModel):
    """Compra a un proveedor (spec 0004a). Creada ▸ En proceso ▸ Finalizada; el stock entra al
    finalizar (RF-COM-26). La fecha es referencia; la de recepción va al kardex (RF-COM-27)."""

    numero = models.IntegerField()  # C-000001 por empresa
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="compras")
    fecha = models.DateField()
    almacen = models.ForeignKey("inventory.Almacen", on_delete=models.PROTECT, related_name="+")
    doc_tipo = models.CharField(max_length=14)
    doc_serie_numero = models.CharField(max_length=20, blank=True)
    igv_pct = _decimal(2)
    subtotal = _decimal(2, default=0)
    igv = _decimal(2, default=0)
    total = _decimal(2, default=0)
    estado = models.CharField(max_length=10, default="CREADA")
    observacion = models.CharField(max_length=250, blank=True)
    fecha_recepcion = models.DateField(null=True)
    guia_remision = models.CharField(max_length=13, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    finalizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    finalizada_en = models.DateTimeField(null=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    anulada_en = models.DateTimeField(null=True)
    motivo_anulacion = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "numero"], name="compra_numero_unico"),
            models.UniqueConstraint(  # RF-COM-11 (RN-COM-02)
                fields=["empresa", "proveedor", "doc_tipo", "doc_serie_numero"],
                condition=~Q(estado="ANULADA") & ~Q(doc_tipo="SIN_DOCUMENTO"),
                name="compra_documento_unico",
            ),
            models.CheckConstraint(
                condition=Q(total=models.F("subtotal") + models.F("igv")), name="compra_total"
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["CREADA", "EN_PROCESO", "FINALIZADA", "ANULADA"])
                & (~Q(estado="FINALIZADA") | Q(fecha_recepcion__isnull=False)),
                name="compra_estado_valido",
            ),
            models.CheckConstraint(  # RF-COM-15, 28, 29: anulada con fecha y motivo
                condition=~Q(estado="ANULADA")
                | (Q(anulada_en__isnull=False) & ~Q(motivo_anulacion="")),
                name="compra_anulada_con_motivo",
            ),
        ]


class CompraLinea(TenantModel):
    """Lo comprado; lo que entra al inventario son sus movimientos (ref COMPRA)."""

    compra = models.ForeignKey(Compra, on_delete=models.PROTECT, related_name="lineas")
    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    cantidad = _decimal(4)
    costo_unitario = _decimal(6)
    es_bonificacion = models.BooleanField(default=False)
    subtotal = _decimal(2)
    lote_codigo = models.CharField(max_length=40, blank=True)
    vencimiento = models.DateField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gt=0)
                & (
                    Q(costo_unitario__gt=0, es_bonificacion=False)
                    | Q(costo_unitario=0, es_bonificacion=True)
                ),
                name="compra_linea_cantidad_y_costo",
            )
        ]
