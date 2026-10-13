"""Modelos de ventas (plan 0006a §2). La base refuerza las reglas del dominio."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from sales.domain.pedido import CANCELADO, CREADO, ESTADOS
from shared.infrastructure.tenant_models import TenantModel


def _decimal(decimales, **kw):
    return models.DecimalField(max_digits=14, decimal_places=decimales, **kw)


def _usuario():
    return models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )


class Cliente(TenantModel):
    """Cliente (RF-VEN-01): CRU, no se elimina; el tipo de documento es la abreviatura del
    maestro de la plataforma (RF-VEN-49)."""

    nombre = models.CharField(max_length=200)
    tipo_doc = models.CharField(max_length=10)
    num_doc = models.CharField(max_length=20, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    email = models.CharField(max_length=120, blank=True)
    comentarios = models.CharField(max_length=500, blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    contacto = models.CharField(max_length=120, blank=True)
    canal = models.CharField(max_length=3, blank=True)  # B2B, B2C o vacío
    es_generico = models.BooleanField(default=False)  # "Clientes varios" (RF-VEN-03)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_doc", "num_doc"],
                condition=~Q(num_doc=""),
                name="cliente_documento_unico",
            ),
            models.UniqueConstraint(
                fields=["empresa"], condition=Q(es_generico=True), name="un_cliente_generico"
            ),
            models.CheckConstraint(  # RF-VEN-05: el genérico no se desactiva
                condition=Q(es_generico=False) | Q(activo=True), name="generico_activo"
            ),
            models.CheckConstraint(condition=Q(canal__in=["", "B2B", "B2C"]), name="cliente_canal"),
        ]

    def __str__(self):
        return self.nombre


class Pedido(TenantModel):
    """Pedido de venta (spec 0006a): Creado ▸ Aprobado ▸ Facturado ▸ Entregado o Cancelado."""

    numero = models.IntegerField()  # P-000001 por empresa
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    fecha_entrega = models.DateField()
    comentario = models.CharField(max_length=250, blank=True)
    estado = models.CharField(max_length=10, default=CREADO)
    total = _decimal(2, default=0)
    creado_por = _usuario()
    creado_en = models.DateTimeField(auto_now_add=True)
    aprobado_por = _usuario()
    aprobado_en = models.DateTimeField(null=True)
    cancelado_por = _usuario()
    cancelado_en = models.DateTimeField(null=True)
    motivo_cancelacion = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "numero"], name="pedido_numero_unico"),
            models.CheckConstraint(
                condition=Q(estado__in=ESTADOS) & Q(total__gte=0), name="pedido_estado_y_total"
            ),
            models.CheckConstraint(  # RF-VEN-37
                condition=~Q(estado=CANCELADO) | ~Q(motivo_cancelacion=""),
                name="pedido_cancelado_con_motivo",
            ),
        ]


class PedidoLinea(TenantModel):
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="lineas")
    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    cantidad = _decimal(4)
    precio = _decimal(2)  # unitario, con impuestos (0002e)
    subtotal = _decimal(2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pedido", "producto"], name="pedido_linea_unica"),
            models.CheckConstraint(
                condition=Q(cantidad__gt=0, precio__gt=0), name="pedido_linea_valida"
            ),
        ]
