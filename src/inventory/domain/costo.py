"""Costo promedio ponderado por producto, sin IGV (spec 0003a, Definiciones; RN-INV-01;
constitución, art. 4.1 y 4.2). Se guarda cantidad y valor totales; el promedio es valor /
cantidad, y con cantidad 0 se conserva el último como referencia."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from inventory.domain.errores import AnulacionConConsumoPosterior

CERO = Decimal("0")
CORREGIR = "La entrada ya tuvo salidas posteriores: corrígela con un ajuste CORRECCION"


def cantidad(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.0001"), ROUND_HALF_UP)


def importe(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def costo_unitario(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.000001"), ROUND_HALF_UP)


@dataclass(frozen=True)
class CostoProducto:
    cantidad: Decimal = CERO
    valor: Decimal = CERO
    promedio: Decimal = CERO  # con cantidad 0: el último, como referencia


def entrada(c: CostoProducto, cant: Decimal, costo: Decimal) -> CostoProducto:
    """RF-INV-18: `valor += cant × costo`; `cantidad += cant`; promedio = valor / cantidad."""
    nueva = cantidad(c.cantidad + cant)
    valor = importe(c.valor + importe(cantidad(cant) * costo_unitario(costo)))
    promedio = costo_unitario(valor / nueva) if nueva else c.promedio
    return CostoProducto(nueva, valor, promedio)


def salida_al_promedio(c: CostoProducto, cant: Decimal) -> tuple[CostoProducto, Decimal]:
    """Sale al promedio sin cambiarlo; la salida que deja 0 sale por el valor restante, sin
    residuo de redondeo (RF-INV-24). El stock suficiente lo valida la existencia (RF-INV-19).
    Devuelve el nuevo costo y el importe de la salida."""
    nueva = cantidad(c.cantidad - cant)
    monto = c.valor if nueva == 0 else importe(cantidad(cant) * c.promedio)
    return CostoProducto(nueva, importe(c.valor - monto), c.promedio), monto


def reversion_de_entrada(
    c: CostoProducto, cant: Decimal, costo_original: Decimal
) -> tuple[CostoProducto, Decimal]:
    """RF-INV-20: sale al costo original de la entrada, así que el promedio sí cambia. Si
    vacía el producto, sale por el valor restante. Si dejaría cantidad o valor negativos, la
    entrada ya se consumió (RF-INV-21)."""
    nueva = cantidad(c.cantidad - cant)
    monto = c.valor if nueva == 0 else importe(cantidad(cant) * costo_unitario(costo_original))
    valor = importe(c.valor - monto)
    if nueva < 0 or valor < 0:
        raise AnulacionConConsumoPosterior(CORREGIR)
    promedio = costo_unitario(valor / nueva) if nueva else c.promedio
    return CostoProducto(nueva, valor, promedio), monto
