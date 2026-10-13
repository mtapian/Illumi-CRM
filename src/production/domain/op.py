"""Orden de producción: estados, componentes, finalización, costo y lote (spec 0005a).

Los componentes se consumen y el producto entra al finalizar, en una sola operación; antes
no hay movimientos (PO, 2026-10-11). Los bienes salen al costo promedio (constitución, art. 4.2).
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from production.domain.errores import OpInvalida

CREADA, EN_PROCESO, FINALIZADA, ANULADA = "CREADA", "EN_PROCESO", "FINALIZADA", "ANULADA"
SERVICIO = "SERVICIO"
CENTIMO, CUATRO, SEIS = Decimal("0.01"), Decimal("0.0001"), Decimal("0.000001")
# (estado, acción) → estado nuevo (Definiciones de la spec; RF-PRD-33)
TRANSICIONES = {
    (CREADA, "editar"): CREADA,
    (EN_PROCESO, "editar"): EN_PROCESO,
    (CREADA, "en_proceso"): EN_PROCESO,
    (EN_PROCESO, "finalizar"): FINALIZADA,
    (CREADA, "anular"): ANULADA,
    (EN_PROCESO, "anular"): ANULADA,
}


@dataclass(frozen=True)
class Componente:
    producto_id: int
    por_consumir: Decimal
    costo_servicio: Decimal | None = None  # solo servicios (RF-PRD-44)


def transicion(estado: str, accion: str) -> str:
    if (estado, accion) in TRANSICIONES:
        return TRANSICIONES[estado, accion]
    if estado == FINALIZADA and accion == "anular":  # RF-PRD-18 (art. 4.5)
        raise OpInvalida("La OP está finalizada: corrígela con un ajuste de inventario")
    if estado == FINALIZADA:
        raise OpInvalida("La OP está finalizada")
    if estado == ANULADA:
        raise OpInvalida("La OP está anulada")
    if accion == "finalizar":
        raise OpInvalida("La OP debe estar en proceso para finalizarla")
    raise OpInvalida("La OP ya está en proceso")


def _cuatro(x: Decimal) -> Decimal:
    return x.quantize(CUATRO, ROUND_HALF_UP)


def _importe(x: Decimal) -> Decimal:
    return x.quantize(CENTIMO, ROUND_HALF_UP)


def copiar_receta(receta, cantidad: Decimal) -> tuple[Componente, ...]:
    """RF-PRD-37: por consumir = cantidad por unidad × cantidad de la OP."""
    return tuple(Componente(c, _cuatro(q * cantidad)) for c, q in receta)


def validar_componentes(producto_id: int, componentes, estados: dict) -> None:
    """RF-PRD-38, 44. `estados`: producto_id → (tipo, activo, sku)."""
    ids = [c.producto_id for c in componentes]
    if producto_id in ids:
        raise OpInvalida("Un producto no puede ser componente de sí mismo", "componentes")
    if len(set(ids)) != len(ids):
        raise OpInvalida("Un componente está repetido en la OP", "componentes")
    for c in componentes:
        tipo, activo, sku = estados.get(c.producto_id, (None, False, str(c.producto_id)))
        if not activo:
            raise OpInvalida(f"El componente {sku} no existe o está inactivo", "componentes")
        if c.por_consumir < 0:
            raise OpInvalida(f"La cantidad de {sku} no puede ser negativa", "componentes")
        if tipo == SERVICIO and (c.costo_servicio is None or c.costo_servicio < 0):
            raise OpInvalida(f"Indica el costo del servicio {sku}", "componentes")
        if tipo != SERVICIO and c.costo_servicio is not None:
            raise OpInvalida("Solo un servicio lleva costo en la OP", "componentes")


def receta_desde_op(componentes, cantidad: Decimal) -> tuple[tuple[int, Decimal], ...]:
    """RF-PRD-38: la lista de la OP como receta por unidad del producto."""
    return tuple(
        (c.producto_id, _cuatro(c.por_consumir / cantidad)) for c in componentes if c.por_consumir
    )


def validar_finalizacion(
    producida: Decimal, motivo: str, n_componentes: int, fecha_fin: date, hoy: date
) -> None:
    """RF-PRD-15, 41, 47: con 0 producido es un lote perdido y exige motivo."""
    if not n_componentes:
        raise OpInvalida("La OP no tiene componentes", "componentes")
    if producida < 0:
        raise OpInvalida("La cantidad producida no puede ser negativa", "producida")
    if producida == 0 and not motivo.strip():
        raise OpInvalida("Indica el motivo del lote perdido", "motivo_perdida")
    if fecha_fin > hoy:
        raise OpInvalida("La fecha de fin no puede ser futura", "fecha_fin")


def faltantes(requeridos: dict[str, Decimal], disponibles: dict[str, Decimal]) -> str | None:
    """RF-PRD-09: todos los faltantes en un mensaje, o None si alcanza."""
    partes = [
        f"{sku} faltan {_cuatro(q - disponibles.get(sku, Decimal('0')))}"
        for sku, q in requeridos.items()
        if q > disponibles.get(sku, Decimal("0"))
    ]
    return f"Stock insuficiente: {'; '.join(partes)}" if partes else None


def validar_stock(requeridos, disponibles) -> None:
    if mensaje := faltantes(requeridos, disponibles):
        raise OpInvalida(mensaje, "componentes")


def costo_total(importes, servicios, indirecto: Decimal) -> Decimal:
    """Componentes consumidos + servicios + costo indirecto (RF-PRD-41, 44)."""
    return _importe(sum((*importes, *servicios, indirecto), Decimal("0")))


def costo_unitario(total: Decimal, producida: Decimal) -> Decimal | None:
    """A 6 decimales (art. 4.1); None en un lote perdido."""
    return (total / producida).quantize(SEIS, ROUND_HALF_UP) if producida else None


def merma(por_consumir: Decimal, consumido: Decimal) -> Decimal:
    """RF-PRD-42: negativa si se usó menos de lo previsto."""
    return _cuatro(consumido - por_consumir)


def rendimiento(programada: Decimal, producida: Decimal) -> Decimal:
    return _importe(producida * 100 / programada)


def excede(programada: Decimal, producida: Decimal) -> bool:
    """RF-PRD-14: se permite, con advertencia."""
    return producida > programada


def sugerir_lote(lotes_por_componente: dict[int, set[str]], sku: str, correlativo: int) -> str:
    """RF-PRD-46: si un solo componente consume un solo lote, ese (el envasado hereda el lote
    del granel); si no, el SKU del producto con un correlativo de 4 dígitos."""
    con_lote = [lotes for lotes in lotes_por_componente.values() if lotes]
    if len(con_lote) == 1 and len(con_lote[0]) == 1:
        return next(iter(con_lote[0]))
    return f"{sku}-{correlativo:04d}"
