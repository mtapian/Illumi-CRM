"""Cobranza de un pedido facturado (spec 0006b, UC-VEN-09): Pendiente ▸ Pagada. Los pagos
se aplican al total, no a una cuota en particular."""

from datetime import date
from decimal import Decimal

from sales.domain.errores import CobranzaInvalida
from sales.domain.facturacion import CERO, Cuota

PENDIENTE, PAGADA = "PENDIENTE", "PAGADA"
ESTADOS = (PENDIENTE, PAGADA)


def estado(total: Decimal, pagado: Decimal) -> str:
    """RF-VEN-54 y 56."""
    return PAGADA if pagado == total else PENDIENTE


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
    return estado_actual == PENDIENTE and monto_vencido(cuotas, pagado, hoy) > 0
