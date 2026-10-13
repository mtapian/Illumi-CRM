"""Cobranza de un pedido facturado (spec 0006b, UC-VEN-09): Pendiente ▸ Parcial ▸ Pagada. Los pagos
se aplican al total, no a una cuota en particular."""

from datetime import date
from decimal import Decimal

from sales.domain.errores import CobranzaInvalida
from sales.domain.facturacion import CERO, Cuota

PENDIENTE, PARCIAL, PAGADA = "PENDIENTE", "PARCIAL", "PAGADA"
ESTADOS = (PENDIENTE, PARCIAL, PAGADA)
ABIERTAS = (PENDIENTE, PARCIAL)


def numero_cobranza(n: int) -> str:
    """Código de la cobranza (PO, 2026-10-13): correlativo por empresa."""
    return f"COB-{n:06d}"


def estado(total: Decimal, pagado: Decimal) -> str:
    """RF-VEN-54 y 56: nada pagado, una parte (PO: Parcial) o todo."""
    if pagado == total:
        return PAGADA
    return PARCIAL if pagado > 0 else PENDIENTE


def validar_pago(estado_actual: str, monto: Decimal, saldo: Decimal) -> None:
    """RF-VEN-55 y 57: nunca mayor al saldo (PO, 2026-10-13)."""
    if estado_actual == PAGADA:
        raise CobranzaInvalida("La cobranza ya está pagada")
    if monto <= 0 or monto > saldo:
        raise CobranzaInvalida(
            f"El pago debe ser mayor a 0 y no superar el saldo ({saldo:.2f})", "monto"
        )


def monto_vencido(cuotas: tuple[Cuota, ...], pagado: Decimal, hoy: date) -> Decimal:
    """RF-VEN-53: Σ cuotas vencidas antes de hoy − pagado, mínimo 0."""
    vencido = sum((x.monto for x in cuotas if x.vencimiento < hoy), CERO)
    return max(vencido - pagado, CERO)


def proximo_vencimiento(cuotas: tuple[Cuota, ...], pagado: Decimal) -> date | None:
    """RF-VEN-53: el de la primera cuota (por vencimiento) que los pagos no cubren."""
    acumulado = CERO
    for x in sorted(cuotas, key=lambda x: x.vencimiento):
        acumulado += x.monto
        if acumulado > pagado:
            return x.vencimiento
    return None


def vencida(estado_actual: str, cuotas: tuple[Cuota, ...], pagado: Decimal, hoy: date) -> bool:
    """RF-VEN-53: indicador, no estado."""
    return estado_actual in ABIERTAS and monto_vencido(cuotas, pagado, hoy) > 0


COBRANZAS_PEDIDO = ("Por cobrar", "Cobro parcial", "Pagado", "Cobro vencido")


def cobranza_del_pedido(
    estado_actual: str, cuotas: tuple[Cuota, ...], pagado: Decimal, hoy: date
) -> str:
    """RF-VEN-68: la cobranza de un pedido facturado en un valor; vencido manda."""
    if vencida(estado_actual, cuotas, pagado, hoy):
        return "Cobro vencido"
    return {PENDIENTE: "Por cobrar", PARCIAL: "Cobro parcial", PAGADA: "Pagado"}[estado_actual]
