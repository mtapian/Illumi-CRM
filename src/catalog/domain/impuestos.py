"""Impuestos de venta y de compra, sus tasas y el desglose de una línea (spec 0002e).

Cada impuesto elige su criterio: porcentaje del valor o monto fijo por unidad vendida
(enmienda 1, PO 2026-10-12); se sugiere % en IGV, EXO e INA y fijo en ISC. Orden fijo:
primero el ISC, después el IGV sobre valor + ISC (contador, 2026-10-10).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from catalog.domain.errores import ImpuestoInvalido
from catalog.domain.precio import Desglose

VENTA, COMPRA = "VENTA", "COMPRA"
IGV, EXO, INA, ISC = "IGV", "EXO", "INA", "ISC"
AFECTACION = (IGV, EXO, INA)  # define si la línea es gravada, exonerada o inafecta
DOS_DECIMALES = Decimal("0.01")
NOMBRE_TIPO = {VENTA: "venta", COMPRA: "compra"}
PORCENTAJE, FIJO = "PORCENTAJE", "FIJO"
CERO = Decimal("0")
Tasa = tuple[str, Decimal]  # (criterio, importe vigente): % o S/ por unidad


def criterio_sugerido(codigo: str) -> str:
    return FIJO if codigo == ISC else PORCENTAJE


@dataclass(frozen=True)
class Impuesto:
    tipo: str
    codigo: str


def validar_impuesto(tipo: str, codigo: str, criterio: str = PORCENTAJE) -> None:
    """RF-CAT-53."""
    if tipo not in NOMBRE_TIPO:
        raise ImpuestoInvalido("El tipo del impuesto es Venta o Compra", "tipo")
    if codigo not in (*AFECTACION, ISC):
        raise ImpuestoInvalido("El código SUNAT es IGV, EXO, INA o ISC", "codigo")
    if criterio not in (PORCENTAJE, FIJO):
        raise ImpuestoInvalido("El criterio es porcentaje o monto fijo", "criterio")
    if codigo == ISC and tipo == COMPRA:
        raise ImpuestoInvalido("El ISC es solo un impuesto de venta", "tipo")


def validar_tasa(codigo: str, importe: Decimal, fechas_existentes: Iterable[date], fecha: date):
    """RF-CAT-54: una tasa por fecha, no negativa, 0 en EXO/INA, hasta 4 decimales."""
    if importe < 0:
        raise ImpuestoInvalido("La tasa no puede ser negativa", "importe")
    if importe.as_tuple().exponent < -4:
        raise ImpuestoInvalido("La tasa admite hasta 4 decimales", "importe")
    if codigo in (EXO, INA) and importe != 0:
        raise ImpuestoInvalido("Un impuesto exonerado o inafecto tiene tasa 0", "importe")
    if fecha in set(fechas_existentes):
        raise ImpuestoInvalido("Ya hay una tasa del impuesto en esa fecha", "desde")


def validar_impuestos(tipo: str, impuestos: list[Impuesto], es_servicio: bool) -> None:
    """RF-CAT-57 y 58: los impuestos de venta o de compra de un producto."""
    for i in impuestos:
        if i.tipo != tipo:
            de, en = NOMBRE_TIPO[i.tipo], NOMBRE_TIPO[tipo]
            raise ImpuestoInvalido(f"Un impuesto de {de} no va en los impuestos de {en}")
    if sum(i.codigo in AFECTACION for i in impuestos) != 1:
        raise ImpuestoInvalido("El producto debe tener un impuesto de IGV, exonerado o inafecto")
    iscs = sum(i.codigo == ISC for i in impuestos)
    if iscs and es_servicio:
        raise ImpuestoInvalido("Un servicio no lleva ISC")
    if iscs > 1:
        raise ImpuestoInvalido("Un producto lleva a lo sumo un ISC")


def desglose_linea(total: Decimal, cantidad: Decimal, afectacion: Tasa, isc: Tasa | None = None):
    """RF-CAT-59 (enmienda 1): `total` incluye impuestos; `afectacion` es el IGV, EXO o INA
    (EXO e INA con importe 0) e `isc` el ISC, si lleva; cada uno como (criterio, importe)."""

    def partes(tasa):  # (monto fijo de la línea, fracción del porcentaje)
        criterio, importe = tasa or (FIJO, CERO)
        return (cantidad * importe, CERO) if criterio == FIJO else (CERO, importe / 100)

    fijo_igv, g = partes(afectacion)
    fijo_isc, s = partes(isc)
    base = (total - fijo_igv) / (1 + g)  # valor + ISC
    valor = ((base - fijo_isc) / (1 + s)).quantize(DOS_DECIMALES, ROUND_HALF_UP)
    isc_linea = (fijo_isc + valor * s).quantize(DOS_DECIMALES, ROUND_HALF_UP)
    return Desglose(valor, isc_linea, total - valor - isc_linea)
