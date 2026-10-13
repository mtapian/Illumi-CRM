"""Modelos de producción (plan 0005a §2 y enmienda 1). La base refuerza las reglas del dominio."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from production.domain.op import ANULADA, CREADA, EN_PROCESO, FINALIZADA
from shared.infrastructure.tenant_models import TenantModel


def _decimal(decimales, **kw):
    return models.DecimalField(max_digits=14, decimal_places=decimales, **kw)


def _usuario(**kw):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+", **kw
    )


class OrdenProduccion(TenantModel):
    """OP (spec 0005a): Creada ▸ En proceso ▸ Finalizada (o Anulada). El stock se mueve solo al
    finalizar (RF-PRD-41); sus movimientos llevan `ref_tipo = "OP"`. Sus productos, con lo
    producido, el lote y el costo de cada uno, son sus salidas (enmienda 1)."""

    numero = models.IntegerField()  # OP-000001 por empresa
    fecha_programada = models.DateField()
    almacen_origen = models.ForeignKey(
        "inventory.Almacen", on_delete=models.PROTECT, related_name="+"
    )
    almacen_destino = models.ForeignKey(
        "inventory.Almacen", on_delete=models.PROTECT, related_name="+"
    )
    responsable = _usuario()
    comentario = models.CharField(max_length=250, blank=True)  # p. ej. el pedido, sin vínculo
    estado = models.CharField(max_length=10, default=CREADA)
    creada_por = _usuario()
    creada_en = models.DateTimeField(auto_now_add=True)
    en_proceso_por = _usuario()
    en_proceso_en = models.DateTimeField(null=True)
    # Al finalizar (RF-PRD-41, 15)
    fecha_fin = models.DateField(null=True)
    costo_indirecto = _decimal(2, default=0)
    costo_total = _decimal(2, default=0)
    motivo_perdida = models.CharField(max_length=200, blank=True)
    perdida = _decimal(2, default=0)  # lote perdido: el costo total, para 0008b
    finalizada_por = _usuario()
    finalizada_en = models.DateTimeField(null=True)
    anulada_por = _usuario()
    anulada_en = models.DateTimeField(null=True)
    motivo_anulacion = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "numero"], name="op_numero_unico"),
            models.CheckConstraint(
                condition=Q(costo_indirecto__gte=0)
                & Q(estado__in=[CREADA, EN_PROCESO, FINALIZADA, ANULADA]),
                name="op_cantidad_y_estado",
            ),
            models.CheckConstraint(  # RF-PRD-41 y 15: con fecha; lote perdido con motivo
                condition=~Q(estado=FINALIZADA)
                | Q(fecha_fin__isnull=False)
                & (
                    Q(perdida=F("costo_total")) & ~Q(motivo_perdida="")
                    | Q(perdida=0, motivo_perdida="")
                ),
                name="op_finalizada",
            ),
            models.CheckConstraint(  # RF-PRD-16
                condition=~Q(estado=ANULADA)
                | Q(anulada_en__isnull=False) & ~Q(motivo_anulacion=""),
                name="op_anulada_con_motivo",
            ),
        ]


class OpSalida(TenantModel):
    """Producto de salida (enmienda 1, RF-PRD-49): cantidad programada y factor de reparto; al
    finalizar, lo producido, su lote y su costo (RF-PRD-52)."""

    op = models.ForeignKey(OrdenProduccion, on_delete=models.PROTECT, related_name="salidas")
    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    cantidad = _decimal(4)
    factor = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    producida = _decimal(4, null=True)
    lote_codigo = models.CharField(max_length=40, blank=True)
    costo_total = _decimal(2, default=0)
    costo_unitario = _decimal(6, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["op", "producto"], name="op_salida_unica"),
            models.CheckConstraint(
                condition=Q(cantidad__gt=0, factor__gt=0)
                & (
                    Q(producida__isnull=True)
                    | Q(producida=0)
                    | Q(producida__gt=0, costo_unitario__isnull=False) & ~Q(lote_codigo="")
                ),
                name="op_salida_valida",
            ),
        ]


class OpComponente(TenantModel):
    """Componente copiado de la receta o agregado en la OP (RF-PRD-37, 38), asignado a una
    salida o común (RF-PRD-51); al finalizar guarda lo consumido, el lote y el costo."""

    op = models.ForeignKey(OrdenProduccion, on_delete=models.PROTECT, related_name="componentes")
    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="+")
    por_consumir = _decimal(4)
    costo_servicio = _decimal(2, null=True)  # solo servicios (RF-PRD-44)
    salida = models.ForeignKey(  # costo directo de esa salida; nulo = común (RF-PRD-51)
        OpSalida, null=True, on_delete=models.PROTECT, related_name="componentes"
    )
    consumido = _decimal(4, null=True)
    lote_codigo = models.CharField(max_length=200, blank=True)  # uno o varios, si la salida reparte
    costo = _decimal(2, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["op", "producto", "salida"],
                nulls_distinct=False,
                name="op_componente_unico",
            ),
            models.CheckConstraint(
                condition=Q(por_consumir__gte=0)
                & (Q(consumido__isnull=True) | Q(consumido__gte=0))
                & (Q(costo_servicio__isnull=True) | Q(costo_servicio__gte=0)),
                name="op_componente_no_negativo",
            ),
        ]
