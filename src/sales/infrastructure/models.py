"""Modelos de ventas (plan 0006a §2). La base refuerza las reglas del dominio."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from sales.domain import cobranza as cob
from sales.domain.facturacion import BOLETA, CONTADO, CREDITO, FACTURA
from sales.domain.pedido import CANCELADO, CREADO, ENTREGADO, ESTADOS, FACTURADO
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
    # Facturación (0006b): el pedido facturado es la venta y su comprobante pendiente.
    comprobante = models.CharField(max_length=7, blank=True)  # sale del cliente (RF-VEN-19)
    forma_pago = models.CharField(max_length=7, blank=True)
    fecha_emision = models.DateField(null=True)
    almacen = models.ForeignKey(
        "inventory.Almacen", on_delete=models.PROTECT, null=True, related_name="+"
    )
    costo_total = _decimal(2, null=True)
    facturado_por = _usuario()
    facturado_en = models.DateTimeField(null=True)
    entregado_por = _usuario()
    entregado_en = models.DateTimeField(null=True)
    token = models.UUIDField(null=True)  # venta directa: un solo registro (RF-VEN-29)

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
            models.CheckConstraint(
                condition=Q(comprobante__in=["", FACTURA, BOLETA])
                & Q(forma_pago__in=["", CONTADO, CREDITO])
                & (~Q(comprobante=BOLETA) | Q(forma_pago=CONTADO)),  # RF-VEN-19
                name="pedido_comprobante_y_forma_pago",
            ),
            models.CheckConstraint(  # RF-VEN-17
                condition=~Q(estado__in=[FACTURADO, ENTREGADO])
                | (
                    ~Q(comprobante="")
                    & ~Q(forma_pago="")
                    & Q(fecha_emision__isnull=False, almacen__isnull=False)
                ),
                name="pedido_facturado_completo",
            ),
            models.CheckConstraint(  # RF-VEN-51
                condition=~Q(estado=ENTREGADO) | Q(entregado_en__isnull=False),
                name="pedido_entregado_con_fecha",
            ),
            models.UniqueConstraint(
                fields=["empresa", "token"],
                condition=Q(token__isnull=False),
                name="pedido_token_unico",
            ),
        ]


class PedidoLinea(TenantModel):
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="lineas")
    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    cantidad = _decimal(4)
    precio = _decimal(2)  # unitario, con impuestos (0002e)
    subtotal = _decimal(2)
    # Al facturar (0006b, RF-VEN-21 y 22): desglose y costo congelado.
    valor = _decimal(2, null=True)
    isc = _decimal(2, null=True)
    igv = _decimal(2, null=True)
    costo = _decimal(2, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pedido", "producto"], name="pedido_linea_unica"),
            models.CheckConstraint(
                condition=Q(cantidad__gt=0, precio__gt=0), name="pedido_linea_valida"
            ),
            models.CheckConstraint(
                condition=Q(valor__isnull=True, isc__isnull=True, igv__isnull=True)
                & Q(costo__isnull=True)
                | Q(costo__isnull=False, costo__gte=0, subtotal=F("valor") + F("isc") + F("igv")),
                name="pedido_linea_desglose",
            ),
        ]


class MetodoPago(TenantModel):
    """Maestro de la empresa (RF-VEN-58, 59): no se elimina, se desactiva."""

    nombre = models.CharField(max_length=60)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "empresa", Lower("nombre"), name="metodo_pago_unico_sin_mayusculas"
            )
        ]

    def __str__(self):
        return self.nombre


class Cobranza(TenantModel):
    """Lo que el cliente debe por un pedido facturado (RF-VEN-17, 53 a 57)."""

    numero = models.IntegerField()  # COB-000001 por empresa (PO)
    pedido = models.OneToOneField(Pedido, on_delete=models.PROTECT, related_name="cobranza")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cobranzas")
    emision = models.DateField()
    total = _decimal(2)
    pagado = _decimal(2, default=0)
    estado = models.CharField(max_length=9, default=cob.PENDIENTE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "numero"], name="cobranza_numero_unico"),
            models.CheckConstraint(
                condition=Q(estado__in=cob.ESTADOS, pagado__gte=0, pagado__lte=F("total")),
                name="cobranza_pagado_valido",
            ),
            models.CheckConstraint(
                condition=Q(estado=cob.PAGADA, pagado=F("total"))
                | Q(estado=cob.PENDIENTE, pagado=0)
                | (Q(estado=cob.PARCIAL, pagado__gt=0) & ~Q(pagado=F("total"))),
                name="cobranza_estado_segun_pagado",
            ),
        ]


class Cuota(TenantModel):
    """Cronograma de la cobranza (RF-VEN-19, 27): inmutable (trigger)."""

    cobranza = models.ForeignKey(Cobranza, on_delete=models.PROTECT, related_name="cuotas")
    numero = models.PositiveSmallIntegerField()
    monto = _decimal(2)
    vencimiento = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cobranza", "numero"], name="cuota_numero_unico"),
            models.CheckConstraint(condition=Q(monto__gt=0), name="cuota_monto_positivo"),
        ]


class Pago(TenantModel):
    """Pago de una cobranza (RF-VEN-54 a 56): no se borra; se anula con motivo (trigger)."""

    cobranza = models.ForeignKey(Cobranza, on_delete=models.PROTECT, related_name="pagos")
    metodo = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, related_name="pagos")
    monto = _decimal(2)
    fecha = models.DateField()
    referencia = models.CharField(max_length=80, blank=True)
    registrado_por = _usuario()
    registrado_en = models.DateTimeField(auto_now_add=True)
    anulado_por = _usuario()
    anulado_en = models.DateTimeField(null=True)
    motivo_anulacion = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="pago_monto_positivo"),
            models.CheckConstraint(
                condition=Q(anulado_en__isnull=True, motivo_anulacion="")
                | (Q(anulado_en__isnull=False) & ~Q(motivo_anulacion="")),
                name="pago_anulado_con_motivo",
            ),
        ]
