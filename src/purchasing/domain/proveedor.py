"""Proveedores y proveedores del producto (spec 0002d; RF-COM-01, RF-COM-21)."""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from purchasing.domain.errores import ProveedorInvalido
from shared.domain.documentos import validar_documento
from shared.domain.errores import DocumentoInvalido

DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True)
class DatosProveedor:
    tipo_doc: str
    num_doc: str
    razon_social: str
    contacto: str = ""
    telefono: str = ""
    email: str = ""
    direccion: str = ""


def validar_proveedor(d: DatosProveedor) -> DatosProveedor:
    """Documento válido (RUC o DNI) y razón social; devuelve los datos sin espacios."""
    try:
        num_doc = validar_documento(d.tipo_doc, d.num_doc)
    except DocumentoInvalido as e:
        e.campo = "num_doc"  # el error va junto al número (docs/ux.md §4)
        raise
    limpios = {c: getattr(d, c).strip() for c in ("razon_social", "contacto", "telefono")}
    limpios |= {c: getattr(d, c).strip() for c in ("email", "direccion")}
    if not limpios["razon_social"]:
        raise ProveedorInvalido("La razón social es obligatoria", "razon_social")
    return replace(d, num_doc=num_doc, **limpios)


def validar_proveedor_producto(se_compra: bool, precio: Decimal, plazo: int) -> Decimal:
    """Solo productos que se compran; precio (S/, 2 decimales half-up) y plazo ≥ 0."""
    if not se_compra:
        raise ProveedorInvalido("El producto no se compra")
    if precio < 0:
        raise ProveedorInvalido("El precio referencial no puede ser negativo")
    if plazo < 0:
        raise ProveedorInvalido("El plazo de entrega no puede ser negativo")
    return precio.quantize(DOS_DECIMALES, ROUND_HALF_UP)
