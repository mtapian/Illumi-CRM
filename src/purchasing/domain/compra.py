"""Compra: líneas, documento del proveedor, totales y guía (spec 0004a; RF-COM-04, 08, 09, 20,
27). El costo de cada línea es el de inventario: sin IGV con factura, el total pagado por
unidad con cualquier otro documento (RF-COM-08)."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from purchasing.domain.errores import CompraInvalida

FACTURA, SIN_DOCUMENTO = "FACTURA", "SIN_DOCUMENTO"
DOCUMENTOS = {
    FACTURA: "factura",
    "BOLETA": "boleta",
    "NOTA_VENTA": "nota de venta",
    SIN_DOCUMENTO: "sin documento",
}
CREADA, EN_PROCESO, FINALIZADA, ANULADA = "CREADA", "EN_PROCESO", "FINALIZADA", "ANULADA"
GUIA = re.compile(r"[A-Z0-9]{4}-\d{1,8}")
CENTIMO = Decimal("0.01")


@dataclass(frozen=True)
class LineaCompra:
    producto_id: int
    cantidad: Decimal
    costo_unitario: Decimal
    bonificacion: bool = False
    lote: str | None = None
    vencimiento: date | None = None


def validar_linea(cantidad: Decimal, costo: Decimal, bonificacion: bool) -> None:
    """Costo 0 solo en una bonificación, y una bonificación solo con costo 0 (RF-COM-04)."""
    if cantidad <= 0:
        raise CompraInvalida("La cantidad debe ser mayor a 0", "lineas")
    if costo < 0:
        raise CompraInvalida("El costo unitario no puede ser negativo", "lineas")
    if bonificacion and costo != 0:
        raise CompraInvalida("Una bonificación tiene costo 0", "lineas")
    if not bonificacion and costo == 0:
        raise CompraInvalida(
            "El costo unitario debe ser mayor a 0; si es una bonificación, márcala", "lineas"
        )


def separa_igv(doc_tipo: str) -> bool:
    return doc_tipo == FACTURA


def _importe(x: Decimal) -> Decimal:
    return x.quantize(CENTIMO, ROUND_HALF_UP)


def subtotal_linea(x: LineaCompra) -> Decimal:
    return _importe(x.cantidad * x.costo_unitario)


def totales(
    lineas: list[LineaCompra], doc_tipo: str, igv: Decimal | list[tuple[str, Decimal]]
) -> tuple[Decimal, Decimal, Decimal]:
    """Subtotal e IGV por línea con half-up a 2 decimales; total = subtotal + IGV (RF-COM-09).
    `igv`: el % de todas las líneas, o el (criterio, importe) de cada una según el impuesto de
    compra de su producto (RF-CAT-61): % del subtotal o monto fijo por unidad."""
    tasas = [("PORCENTAJE", igv)] * len(lineas) if isinstance(igv, Decimal) else igv
    subtotal = total_igv = Decimal("0.00")
    for x, (criterio, importe) in zip(lineas, tasas, strict=True):
        sub = subtotal_linea(x)
        subtotal += sub
        if separa_igv(doc_tipo):
            base = x.cantidad if criterio == "FIJO" else sub / 100
            total_igv += _importe(base * importe)
    return subtotal, total_igv, subtotal + total_igv


def validar_documento_compra(doc_tipo: str, serie_numero: str, tipo_doc_proveedor: str) -> str:
    """Devuelve la serie-número normalizada ("" sin documento; RF-COM-20)."""
    if doc_tipo not in DOCUMENTOS:
        raise CompraInvalida("Tipo de documento inválido", "doc_tipo")
    if doc_tipo == SIN_DOCUMENTO:
        return ""
    serie_numero = serie_numero.strip().upper()
    if not serie_numero:
        raise CompraInvalida("Indica la serie y el número del documento", "doc_serie_numero")
    if doc_tipo == FACTURA and tipo_doc_proveedor != "RUC":
        raise CompraInvalida("Una factura requiere un proveedor con RUC", "doc_tipo")
    return serie_numero


def validar_guia(guia: str) -> str:
    """Guía de remisión opcional: serie de 4 caracteres, guion y hasta 8 dígitos (RF-COM-27)."""
    guia = guia.strip().upper()
    if guia and not GUIA.fullmatch(guia):
        raise CompraInvalida("Guía de remisión inválida", "guia")
    return guia


def numero_compra(numero: int) -> str:
    return f"C-{numero:06d}"
