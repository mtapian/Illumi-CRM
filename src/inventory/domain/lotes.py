"""Lotes y vencimientos (spec 0003a; RF-INV-23, 25, 26; RF-CAT-37 y 40)."""

from datetime import date, timedelta

from inventory.domain.errores import LoteConOtroVencimiento, LoteVencido, ServicioSinStock
from inventory.domain.existencia import Existencia

MERMA = "MERMA"


def lote_vencido(vencimiento: date | None, hoy: date) -> bool:
    """El día del vencimiento todavía se puede vender (RN-INV-07)."""
    return vencimiento is not None and vencimiento < hoy


def validar_salida_de_lote(e: Existencia, motivo: str, hoy: date) -> None:
    """RF-INV-23: un lote vencido solo sale por merma."""
    if lote_vencido(e.vencimiento, hoy) and motivo != MERMA:
        raise LoteVencido(f"El lote {e.lote} está vencido: solo puede salir por merma")


def validar_bien(tipo: str) -> None:
    """RF-INV-25: solo los bienes llevan stock (RF-CAT-37)."""
    if tipo == "SERVICIO":
        raise ServicioSinStock("Un servicio no lleva stock")


def sugerir_vencimiento(ingreso: date, vida_util_dias: int | None) -> date | None:
    """RF-INV-26: la vida útil del producto solo sugiere el vencimiento (RF-CAT-40)."""
    return ingreso + timedelta(days=vida_util_dias) if vida_util_dias else None


def validar_lote_existente(codigo: str, actual: date | None, indicado: date | None) -> None:
    """RF-INV-26: un lote que ya existe conserva su vencimiento; sin indicar, usa el suyo."""
    if indicado is None or indicado == actual:
        return
    if actual is None:
        raise LoteConOtroVencimiento(f"El lote {codigo} ya existe sin vencimiento")
    raise LoteConOtroVencimiento(f"El lote {codigo} ya existe con vencimiento {actual:%Y-%m-%d}")
