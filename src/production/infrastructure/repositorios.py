"""Persistencia de las OP (plan 0005a §2)."""

from django.shortcuts import get_object_or_404
from django.utils import timezone

from inventory.infrastructure.models import Almacen, Lote
from production.application.ordenes import EJECUTAR, DatosOp
from production.domain.op import ANULADA, EN_PROCESO, FINALIZADA, Componente, Salida
from production.infrastructure.models import OpComponente, OpSalida, OrdenProduccion
from shared.domain.tenant import empresa_actual
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import Usuario


def _datos(op: OrdenProduccion) -> DatosOp:
    return DatosOp(
        tuple(Salida(x.producto_id, x.cantidad, x.factor) for x in op.salidas.order_by("id")),
        op.fecha_programada,
        op.almacen_origen_id,
        op.almacen_destino_id,
        op.responsable_id,
        op.comentario,
        tuple(
            Componente(
                c.producto_id,
                c.por_consumir,
                c.costo_servicio,
                c.salida.producto_id if c.salida_id else None,
            )
            for c in op.componentes.select_related("salida").order_by("id")
        ),
    )


_CABECERA = (
    "fecha_programada",
    "almacen_origen_id",
    "almacen_destino_id",
    "responsable_id",
    "comentario",
)


class OrdenesOrm:
    def almacen_activo(self, almacen_id):
        fila = Almacen.objects.filter(pk=almacen_id).values_list("activo", flat=True).first()
        return fila

    def responsables(self) -> dict[int, str]:
        """Usuarios activos de la empresa que pueden ejecutar OP (RF-PRD-35)."""
        hoy = timezone.localdate()
        usuarios = Usuario.objects.filter(
            empresa_id=empresa_actual(), is_active=True, es_tecnico=False
        )
        return {
            u.id: u.nombre or u.email
            for u in usuarios.order_by("nombre", "email")
            if EJECUTAR in actor_de(u, hoy).permisos
        }

    def _guardar_detalle(self, op_id, datos) -> None:
        """Reemplaza salidas y componentes; cada componente apunta a su salida (RF-PRD-51)."""
        OpComponente.objects.filter(op_id=op_id).delete()
        OpSalida.objects.filter(op_id=op_id).delete()
        empresa = empresa_actual()
        salidas = {
            x.producto_id: OpSalida.objects.create(
                empresa_id=empresa,
                op_id=op_id,
                producto_id=x.producto_id,
                cantidad=x.cantidad,
                factor=x.factor,
            )
            for x in datos.salidas
        }
        OpComponente.objects.bulk_create(
            OpComponente(
                empresa_id=empresa,
                op_id=op_id,
                producto_id=c.producto_id,
                por_consumir=c.por_consumir,
                costo_servicio=c.costo_servicio,
                salida=salidas.get(c.salida),
            )
            for c in datos.componentes
        )

    def crear(self, numero, datos, usuario_id) -> int:
        cabecera = {c: getattr(datos, c) for c in _CABECERA}
        op = OrdenProduccion.objects.create(numero=numero, creada_por_id=usuario_id, **cabecera)
        self._guardar_detalle(op.id, datos)
        return op.id

    def actualizar(self, op_id, datos) -> None:
        OrdenProduccion.objects.filter(pk=op_id).update(**{c: getattr(datos, c) for c in _CABECERA})
        self._guardar_detalle(op_id, datos)

    def bloquear(self, op_id):
        op = get_object_or_404(OrdenProduccion.objects.select_for_update(of=("self",)), pk=op_id)
        return op.estado, _datos(op)

    def en_proceso(self, op_id, usuario_id) -> None:
        OrdenProduccion.objects.filter(pk=op_id).update(
            estado=EN_PROCESO, en_proceso_por_id=usuario_id, en_proceso_en=timezone.now()
        )

    def anular(self, op_id, usuario_id, motivo) -> None:
        OrdenProduccion.objects.filter(pk=op_id).update(
            estado=ANULADA,
            anulada_por_id=usuario_id,
            anulada_en=timezone.now(),
            motivo_anulacion=motivo,
        )

    def correlativo_lote(self, producto_id) -> int:
        return Lote.objects.filter(producto_id=producto_id).count() + 1

    def finalizar(self, op_id, f, componentes, salidas, total, usuario_id) -> None:
        """Componentes y salidas se guardan antes del estado: el trigger los bloquea al
        finalizar."""
        for c in componentes:
            filas = OpComponente.objects.filter(op_id=op_id, producto_id=c.producto_id)
            filas = (
                filas.filter(salida__producto_id=c.salida)
                if c.salida
                else filas.filter(salida__isnull=True)
            )
            filas.update(consumido=c.consumido, lote_codigo=c.lotes, costo=c.costo)
        for x in salidas:
            OpSalida.objects.filter(op_id=op_id, producto_id=x.producto_id).update(
                producida=x.producida,
                lote_codigo=x.lote,
                costo_total=x.costo,
                costo_unitario=x.unitario,
            )
        perdida = not any(x.producida for x in salidas)
        OrdenProduccion.objects.filter(pk=op_id).update(
            estado=FINALIZADA,
            fecha_fin=f.fecha_fin,
            costo_indirecto=f.costo_indirecto,
            costo_total=total,
            motivo_perdida=f.motivo_perdida.strip() if perdida else "",
            perdida=total if perdida else 0,
            finalizada_por_id=usuario_id,
            finalizada_en=timezone.now(),
        )
