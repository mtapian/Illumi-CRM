"""Validación de un producto según su tipo (spec 0002a; RN-CAT-01 a 03, 06 a 09)."""

from dataclasses import dataclass, replace
from decimal import Decimal

from catalog.domain.errores import ProductoInvalido
from catalog.domain.tipos import TipoProducto as T

LITROS = "L"
_COMUNES = {"sku", "nombre", "tipo", "unidad", "familia_id", "stock_minimo", "activo"}
_PROPIOS = {
    T.INSUMO: set(),
    T.ENVASE: set(),
    T.GRANEL: {"vida_util_dias", "prefijo_lote"},
    T.TERMINADO: {"precio_venta", "isc_categoria_id", "vida_util_dias"},
    T.MERCADERIA: {
        "precio_venta",
        "isc_categoria_id",
        "contenido_litros",
        "controla_lote",
        "vida_util_dias",
    },
}
INMUTABLES_CON_MOVIMIENTOS = ("sku", "tipo", "unidad", "controla_lote")  # RF-CAT-09


@dataclass(frozen=True)
class DatosProducto:
    sku: str
    nombre: str
    tipo: T
    unidad: str  # abreviatura (UND, KG, L…)
    familia_id: int | None = None
    stock_minimo: Decimal = Decimal("0")
    activo: bool = True
    controla_lote: bool = False
    precio_venta: Decimal | None = None
    isc_categoria_id: int | None = None
    contenido_litros: Decimal | None = None
    vida_util_dias: int | None = None
    prefijo_lote: str | None = None


def campos_requeridos(tipo: T) -> set[str]:
    """Campos que se piden para el tipo: los comunes y los propios (RF-CAT-04 a 07)."""
    return _COMUNES | _PROPIOS[T(tipo)]


def validar_producto(d: DatosProducto) -> DatosProducto:
    """Devuelve el producto normalizado: sin campos ajenos a su tipo y con su lote."""
    tipo = T(d.tipo)
    propios = _PROPIOS[tipo]
    limpio = {c: None for c in _PROPIOS[T.MERCADERIA] if c not in propios}
    limpio.pop("controla_lote", None)
    d = replace(d, sku=d.sku.strip().upper(), nombre=d.nombre.strip(), **limpio)
    if not d.sku:
        raise ProductoInvalido("El SKU es obligatorio")
    if not d.nombre:
        raise ProductoInvalido("El nombre es obligatorio")
    if d.stock_minimo < 0:
        raise ProductoInvalido("El stock mínimo no puede ser negativo")
    lote = tipo.lote_siempre or (tipo == T.MERCADERIA and d.controla_lote)
    d = replace(d, controla_lote=lote)
    if tipo == T.GRANEL:
        if d.unidad != LITROS:
            raise ProductoInvalido("El granel debe medirse en litros")
        d = replace(d, prefijo_lote=(d.prefijo_lote or d.nombre[:3]).strip().upper())
    if tipo.vendible and (d.precio_venta is None or d.precio_venta <= 0):
        raise ProductoInvalido("El precio de venta es obligatorio y debe ser mayor a 0")
    if tipo == T.TERMINADO and not (d.vida_util_dias or 0) > 0:
        raise ProductoInvalido("La vida útil debe ser mayor a 0 días")  # RN-CAT-09
    if tipo == T.MERCADERIA and d.controla_lote and not (d.vida_util_dias or 0) > 0:
        raise ProductoInvalido("Indica la vida útil sugerida en días para controlar lotes")
    if tipo == T.MERCADERIA and d.isc_categoria_id and not d.contenido_litros:
        # El ISC del MVP es por litro; el terminado toma el contenido de su presentación.
        raise ProductoInvalido(
            "Un producto con ISC por litro requiere el contenido en litros por unidad"
        )  # RF-CAT-26
    if d.contenido_litros is not None and d.contenido_litros <= 0:
        raise ProductoInvalido("El contenido en litros debe ser mayor a 0")
    return d


def cambios_prohibidos(original: DatosProducto, nuevo: DatosProducto, tiene_movimientos: bool):
    if not tiene_movimientos:
        return []
    return [c for c in INMUTABLES_CON_MOVIMIENTOS if getattr(original, c) != getattr(nuevo, c)]


def cabe_en_limite(activos: int, limite: int | None) -> bool:
    """Cuentan los productos activos de todos los tipos (RF-CAT-10, RN-CAT-07)."""
    return limite is None or activos < limite


def puede_desactivar(stock: Decimal, granel_con_presentaciones: bool) -> str | None:
    """None si se puede; si no, qué hacer primero (RF-CAT-20, RN-CAT-08)."""
    if stock > 0:
        return "El producto tiene stock. Ajusta el stock a cero antes de desactivarlo"
    if granel_con_presentaciones:
        return "Desactiva primero las presentaciones de este granel"
    return None


def puede_eliminar(tiene_movimientos: bool, referencias: int) -> bool:
    """Solo sin movimientos ni referencias en recetas, presentaciones o pedidos (RF-CAT-21)."""
    return not tiene_movimientos and referencias == 0
