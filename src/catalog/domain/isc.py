"""ISC por Sistema Específico: monto fijo en S/ por litro con vigencia (spec 0002c; RN-CAT-10)."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

DOS_DECIMALES = Decimal("0.01")
ESPECIFICO = "ESPECIFICO"  # único sistema del MVP (RF-CAT-23)
CODIGO_TRIBUTO = "2000"  # ISC en el catálogo 05 de SUNAT


@dataclass(frozen=True)
class Tarifa:
    vigente_desde: date
    monto_por_litro: Decimal


def tarifa_aplicable(tarifas, fecha: date) -> Tarifa | None:
    """La de mayor `vigente_desde` que sea ≤ la fecha de emisión (RF-CAT-25)."""
    vigentes = [t for t in tarifas if t.vigente_desde <= fecha]
    return max(vigentes, key=lambda t: t.vigente_desde) if vigentes else None


def isc_linea(cantidad: Decimal, contenido_litros: Decimal, tarifa: Tarifa | None) -> Decimal:
    """`cantidad × contenido × monto por litro`, a 2 decimales half-up; 0 sin ISC (RF-CAT-27)."""
    if tarifa is None:
        return Decimal("0.00")
    monto = cantidad * contenido_litros * tarifa.monto_por_litro
    return monto.quantize(DOS_DECIMALES, ROUND_HALF_UP)


def contenido_sugerido(receta, unidades: dict[int, str]) -> Decimal | None:
    """Litros por unidad sugeridos desde la receta: suma de los componentes en L (RF-CAT-45)."""
    litros = [q for c, q in receta if unidades.get(c) == "L"]
    return sum(litros, Decimal("0")).quantize(Decimal("0.0001")) if litros else None
