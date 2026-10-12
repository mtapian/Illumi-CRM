"""Impuestos de venta y de compra, sus tasas y el desglose de una línea (spec 0002e).

El criterio lo define el código: IGV, EXO e INA son un porcentaje; el ISC es un monto fijo
por unidad vendida (Sistema Específico). Orden fijo: primero el ISC, después el IGV sobre
valor + ISC (contador, 2026-10-10).
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


@dataclass(frozen=True)
class Impuesto:
    tipo: str
    codigo: str


def validar_impuesto(tipo: str, codigo: str) -> None:
    """RF-CAT-53."""
    if tipo not in NOMBRE_TIPO:
        raise ImpuestoInvalido("El tipo del impuesto es Venta o Compra")
    if codigo not in (*AFECTACION, ISC):
        raise ImpuestoInvalido("El código SUNAT es IGV, EXO, INA o ISC")
    if codigo == ISC and tipo == COMPRA:
        raise ImpuestoInvalido("El ISC es solo un impuesto de venta")


def validar_tasa(codigo: str, importe: Decimal, fechas_existentes: Iterable[date], fecha: date):
    """RF-CAT-54: una tasa por fecha, no negativa, 0 en EXO/INA, hasta 4 decimales."""
    if importe < 0:
        raise ImpuestoInvalido("La tasa no puede ser negativa")
    if importe.as_tuple().exponent < -4:
        raise ImpuestoInvalido("La tasa admite hasta 4 decimales")
    if codigo in (EXO, INA) and importe != 0:
        raise ImpuestoInvalido("Un impuesto exonerado o inafecto tiene tasa 0")
    if fecha in set(fechas_existentes):
        raise ImpuestoInvalido("Ya hay una tasa del impuesto en esa fecha")


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


def desglose_linea(total: Decimal, cantidad: Decimal, igv_pct: Decimal, isc_monto: Decimal):
    """RF-CAT-59: `total` incluye impuestos; igv_pct = 0 en EXO/INA; isc_monto = 0 sin ISC."""
    base = total / (1 + igv_pct / 100)
    isc = (cantidad * isc_monto).quantize(DOS_DECIMALES, ROUND_HALF_UP)
    valor = (base - isc).quantize(DOS_DECIMALES, ROUND_HALF_UP)
    return Desglose(valor, isc, total - valor - isc)
