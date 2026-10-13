"""Reglas de la facturación de un pedido (spec 0006b, UC-VEN-05 y 07)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sales.domain.errores import PedidoInvalido

FACTURA, BOLETA = "FACTURA", "BOLETA"
CONTADO, CREDITO = "CONTADO", "CREDITO"
CERO = Decimal("0")


@dataclass(frozen=True)
class Cuota:
    monto: Decimal
    vencimiento: date


def comprobante_para(tipo_doc: str) -> str:
    """RF-VEN-19 y 24 (RN-VEN-02): Factura si el cliente tiene RUC; Boleta en otro caso."""
    return FACTURA if tipo_doc == "RUC" else BOLETA


def validar_boleta(es_generico: bool, total: Decimal, umbral: Decimal) -> None:
    """RF-VEN-25 (RN-VEN-03)."""
    if es_generico and total > umbral:
        raise PedidoInvalido(
            f"Las boletas mayores a S/ {umbral:.2f} requieren identificar al cliente", "cliente"
        )


def vencimiento_en(emision: date, dias: int) -> date:
    """RF-VEN-19: la cuota se ingresa en días desde la emisión."""
    return emision + timedelta(days=dias)


def cronograma(
    forma: str, comprobante: str, cuotas: tuple[Cuota, ...], total: Decimal, emision: date
) -> tuple[Cuota, ...]:
    """RF-VEN-19 y 27 (RN-VEN-08): al contado, una cuota por el total en la emisión; a
    crédito, solo factura, con cuotas > 0, posteriores a la emisión y que suman el total."""
    if forma != CREDITO:
        return (Cuota(total, emision),)
    if comprobante != FACTURA:
        raise PedidoInvalido("La venta a crédito requiere factura (cliente con RUC)", "forma_pago")
    if not cuotas:
        raise PedidoInvalido("Una venta a crédito requiere al menos una cuota", "cuotas")
    if any(x.monto <= 0 for x in cuotas):
        raise PedidoInvalido("Cada cuota debe tener un monto mayor a 0", "cuotas")
    if any(x.vencimiento <= emision for x in cuotas):
        raise PedidoInvalido(
            "El vencimiento de cada cuota debe ser posterior a la emisión", "cuotas"
        )
    suma = sum((x.monto for x in cuotas), CERO)
    if suma != total:
        raise PedidoInvalido(
            f"La suma de las cuotas ({suma:.2f}) debe ser igual al monto pendiente ({total:.2f})",
            "cuotas",
        )
    return tuple(sorted(cuotas, key=lambda x: x.vencimiento))


def validar_valor(sku: str, valor: Decimal) -> None:
    """RF-VEN-28."""
    if valor <= 0:
        raise PedidoInvalido(f"{sku}: el ISC deja el valor en 0 o menos", "lineas")


def validar_pagos_directa(montos: Iterable[Decimal], total: Decimal) -> None:
    """RF-VEN-52: los pagos de una venta directa suman exactamente su total."""
    montos = list(montos)
    if any(m <= 0 for m in montos):
        raise PedidoInvalido("Cada pago debe ser mayor a 0", "pagos")
    suma = sum(montos, CERO)
    if suma != total:
        raise PedidoInvalido(f"Los pagos ({suma:.2f}) deben sumar el total ({total:.2f})", "pagos")
