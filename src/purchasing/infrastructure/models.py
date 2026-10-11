"""Modelos de compras (plan 0002d §2). La base refuerza las reglas del dominio."""

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
