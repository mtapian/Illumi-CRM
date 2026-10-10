"""Presentación de un TERMINADO: granel de origen + contenido + materiales por unidad
(spec 0002b; RN-CAT-04, 05)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from catalog.domain.errores import PresentacionInvalida
from catalog.domain.tipos import TipoProducto as T

CUATRO_DECIMALES = Decimal("0.0001")  # cantidades (RN-GEN-09)


@dataclass(frozen=True)
class DatosPresentacion:
    granel_id: int
    contenido_litros: Decimal
    materiales: tuple[tuple[int, Decimal], ...]  # (material_id, cantidad por unidad)


def validar_presentacion(granel: tuple[T, bool], contenido: Decimal, materiales) -> None:
    """`granel` = (tipo, activo); `materiales` = [(tipo, cantidad por unidad)]."""
    tipo, activo = granel
    if tipo != T.GRANEL:
        raise PresentacionInvalida("El origen debe ser un producto tipo GRANEL")
    if not activo:
        raise PresentacionInvalida("El granel de origen está inactivo")
    if contenido is None or contenido <= 0:
        raise PresentacionInvalida("El contenido debe ser mayor a 0 litros")
    if not materiales:
        raise PresentacionInvalida("La presentación requiere al menos un material de envase")
    if any(t != T.ENVASE for t, _ in materiales):
        raise PresentacionInvalida("Los materiales deben ser productos tipo ENVASE")
    if any(c is None or c <= 0 for _, c in materiales):
        raise PresentacionInvalida("La cantidad de cada material debe ser mayor a 0")


def materiales_para(materiales: dict[int, Decimal], unidades: Decimal) -> dict[int, Decimal]:
    """Material → cantidad para envasar `unidades` (4 decimales, half-up). La usa 0005b."""
    return {
        m: (c * unidades).quantize(CUATRO_DECIMALES, ROUND_HALF_UP) for m, c in materiales.items()
    }
