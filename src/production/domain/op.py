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
class Salida:
    """Producto de salida de la OP (enmienda 1, RF-PRD-49)."""

    producto_id: int
    cantidad: Decimal
    factor: Decimal = Decimal("1")  # reparto del costo común (RF-PRD-52)


@dataclass(frozen=True)
class Componente:
    producto_id: int
    por_consumir: Decimal
    costo_servicio: Decimal | None = None  # solo servicios (RF-PRD-44)
    salida: int | None = None  # producto de salida al que se asigna; None = común (RF-PRD-51)


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


def copiar_receta(receta, cantidad: Decimal, salida: int | None = None) -> tuple[Componente, ...]:
    """RF-PRD-37, 50: cantidad por unidad × cantidad de la salida, asignado a ella."""
    return tuple(Componente(c, _cuatro(q * cantidad), salida=salida) for c, q in receta)


def factor_sugerido(litros: Decimal | None) -> Decimal:
    """RF-PRD-49: los litros por unidad del producto (botella 0.33, barril 20); si no, 1."""
    return _cuatro(litros) if litros else Decimal("1")


def validar_salidas(salidas) -> None:
    """RF-PRD-49: al menos una, sin repetir, cantidad y factor mayores a 0."""
    if not salidas:
        raise OpInvalida("Indica al menos un producto de salida", "salidas")
    ids = [x.producto_id for x in salidas]
    if len(set(ids)) != len(ids):
        raise OpInvalida("Un producto de salida está repetido", "salidas")
    if any(x.cantidad <= 0 for x in salidas):
        raise OpInvalida("La cantidad debe ser mayor a 0", "salidas")
    if any(x.factor <= 0 for x in salidas):
        raise OpInvalida("El factor de reparto debe ser mayor a 0", "salidas")


def validar_componentes(salidas: set[int], componentes, estados: dict) -> None:
    """RF-PRD-38, 44, 51. `salidas`: productos de salida; `estados`: producto_id → (tipo,
    activo, sku). Un componente se repite solo asignado a otra salida."""
    claves = [(c.producto_id, c.salida) for c in componentes]
    if any(c.producto_id in salidas for c in componentes):
        raise OpInvalida("Un producto no puede ser componente de sí mismo", "componentes")
    if len(set(claves)) != len(claves):
        raise OpInvalida("Un componente está repetido en la OP", "componentes")
    for c in componentes:
        if c.salida is not None and c.salida not in salidas:
            raise OpInvalida(
                "El componente se asigna a algo que no es un producto de salida de la OP",
                "componentes",
            )
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


def validar_finalizacion(producida: Decimal, motivo: str, fecha_fin: date, hoy: date) -> None:
    """RF-PRD-15, 41: con 0 producido es un lote perdido y exige motivo. Los componentes no
    son obligatorios (RF-PRD-47, PO 2026-10-12)."""
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


def repartir(salidas, directos: dict, comunes: Decimal, indirecto: Decimal) -> dict:
    """RF-PRD-52. `salidas`: (clave, producida, factor). Cada salida carga sus directos y una
    parte de lo común y del indirecto por producida × factor; lo asignado a una salida con 0
    pasa a lo común; el redondeo se ajusta en la última. Todas en 0: lote perdido (0 a todas)."""
    producen = [(k, p * f) for k, p, f in salidas if p > 0]
    if not producen:
        return {k: Decimal("0") for k, _, _ in salidas}
    comun = (
        comunes
        + indirecto
        + sum((directos.get(k, Decimal("0")) for k, p, _ in salidas if p <= 0), Decimal("0"))
    )
    total_peso = sum((peso for _, peso in producen), Decimal("0"))
    costos, repartido = {k: Decimal("0") for k, _, _ in salidas}, Decimal("0")
    for n, (k, peso) in enumerate(producen):
        parte = comun - repartido if n == len(producen) - 1 else _importe(comun * peso / total_peso)
        repartido += parte
        costos[k] = _importe(directos.get(k, Decimal("0")) + parte)
    return costos


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
