"""Validación de un producto: bien o servicio y sus casillas (spec 0002a, enmienda 4)."""

from dataclasses import asdict, dataclass, replace
from decimal import Decimal

from catalog.domain.errores import ProductoInvalido
from catalog.domain.isc import ESPECIFICO
from catalog.domain.tipos import TipoProducto as T

CASILLAS = ("se_vende", "se_compra", "se_fabrica")  # RF-CAT-38
INMUTABLES_CON_MOVIMIENTOS = ("sku", "tipo", "unidad")  # RF-CAT-43
SIN_CASILLAS = "Marca al menos una opción: se vende, se compra o se fabrica"


@dataclass(frozen=True)
class DatosProducto:
    sku: str
    nombre: str
    tipo: T
    unidad: str  # abreviatura (UND, KG, L…)
    categoria_id: int | None = None  # RF-CAT-49 (antes "familia")
    stock_minimo: Decimal = Decimal("0")
    activo: bool = True
    se_vende: bool = False
    se_compra: bool = True  # un bien nuevo se compra por defecto (RF-CAT-38)
    se_fabrica: bool = False
    precio_venta: Decimal | None = None
    isc_sistema: str | None = None  # "ESPECIFICO" = afecto a ISC (RF-CAT-45); None = no afecto
    isc_codigo_tipo_sistema: str = ""  # para el comprobante (01 o 02: dato del producto)
    contenido_litros: Decimal | None = None  # unidad de control del ISC (RF-CAT-26, 45)
    vida_util_dias: int | None = None  # solo sugiere el vencimiento del lote (RF-CAT-40)
    peso_kg: Decimal | None = None  # RF-CAT-42
    volumen_m3: Decimal | None = None
    referencia: str = ""  # RF-CAT-31
    codigo_barras: str = ""
    marca_id: int | None = None  # RF-CAT-33

    @property
    def afecto_isc(self) -> bool:
        return self.isc_sistema is not None


def validar_producto(d: DatosProducto) -> DatosProducto:
    """Devuelve el producto normalizado, sin los campos que sus casillas no usan."""
    tipo = T(d.tipo)
    d = replace(
        d,
        tipo=tipo,
        sku=d.sku.strip().upper(),
        nombre=d.nombre.strip(),
        referencia=d.referencia.strip(),
        codigo_barras=d.codigo_barras.strip(),
    )
    if not d.sku:
        raise ProductoInvalido("El SKU es obligatorio", "sku")
    if not d.nombre:
        raise ProductoInvalido("El nombre es obligatorio", "nombre")
    if tipo == T.SERVICIO:  # RF-CAT-37: sin inventario ni ISC
        if d.se_fabrica:
            raise ProductoInvalido("Un servicio no se fabrica", "se_fabrica")
        d = replace(
            d,
            stock_minimo=Decimal("0"),
            vida_util_dias=None,
            peso_kg=None,
            volumen_m3=None,
            isc_sistema=None,
            isc_codigo_tipo_sistema="",
            contenido_litros=None,
        )
    if not any(getattr(d, c) for c in CASILLAS):
        raise ProductoInvalido(SIN_CASILLAS, "se_vende")
    if not d.se_vende:  # RF-CAT-39: precio e ISC solo si se vende
        d = replace(
            d,
            precio_venta=None,
            isc_sistema=None,
            isc_codigo_tipo_sistema="",
            contenido_litros=None,
        )
    elif d.precio_venta is None or d.precio_venta <= 0:
        raise ProductoInvalido(
            "El precio de venta es obligatorio y debe ser mayor a 0", "precio_venta"
        )
    if d.stock_minimo < 0:
        raise ProductoInvalido("El stock mínimo no puede ser negativo", "stock_minimo")
    if d.vida_util_dias is not None and d.vida_util_dias <= 0:
        raise ProductoInvalido("La vida útil debe ser mayor a 0 días", "vida_util_dias")
    if d.peso_kg is not None and d.peso_kg < 0:
        raise ProductoInvalido("El peso no puede ser negativo", "peso_kg")
    if d.volumen_m3 is not None and d.volumen_m3 < 0:
        raise ProductoInvalido("El volumen no puede ser negativo", "volumen_m3")
    if d.isc_sistema is None:
        d = replace(d, isc_codigo_tipo_sistema="")
    elif d.isc_sistema != ESPECIFICO:
        raise ProductoInvalido(
            "El MVP solo admite el ISC por Sistema Específico", "afecto_isc"
        )  # RF-CAT-23
    elif not d.contenido_litros:
        raise ProductoInvalido(
            "Un producto con ISC por litro requiere el contenido en litros por unidad",
            "contenido_litros",
        )  # RF-CAT-26
    elif not d.isc_codigo_tipo_sistema.strip():
        raise ProductoInvalido(
            "Indica el código de tipo de sistema del ISC", "isc_codigo_tipo_sistema"
        )
    if d.contenido_litros is not None and d.contenido_litros <= 0:
        raise ProductoInvalido("El contenido en litros debe ser mayor a 0", "contenido_litros")
    return d


def cambios_prohibidos(original: DatosProducto, nuevo: DatosProducto, tiene_movimientos: bool):
    if not tiene_movimientos:
        return []
    return [c for c in INMUTABLES_CON_MOVIMIENTOS if getattr(original, c) != getattr(nuevo, c)]


def cabe_en_limite(activos: int, limite: int | None) -> bool:
    """Cuentan los productos activos de todos los tipos (RF-CAT-10, RN-CAT-07)."""
    return limite is None or activos < limite


def puede_desactivar(stock: Decimal) -> str | None:
    """None si se puede; si no, qué hacer primero (RF-CAT-20, RN-CAT-08)."""
    if stock > 0:
        return "El producto tiene stock. Ajusta el stock a cero antes de desactivarlo"
    return None


def puede_eliminar(tiene_movimientos: bool, referencias: int) -> bool:
    """Solo sin movimientos ni referencias en recetas u otros documentos (RF-CAT-21)."""
    return not tiene_movimientos and referencias == 0


def _texto(valor):
    if isinstance(valor, Decimal):
        return format(valor.normalize(), "f")
    return str(valor) if isinstance(valor, T) else valor


def instantanea(d: DatosProducto, receta=None) -> dict:
    """Datos del producto como texto para su historial, sin el estado (RF-CAT-32).

    ponytail: categoría, marca y componentes se guardan por id; mostrar nombres si el PO lo pide.
    `receta`: tuplas (componente, cantidad), o None si no se toca.
    """
    datos = {c: _texto(v) for c, v in asdict(d).items() if c != "activo"}
    if receta is not None:
        datos["receta"] = [f"{m} × {_texto(c)}" for m, c in receta]
    return datos


def solo_cambios(antes: dict, despues: dict) -> tuple[dict, dict]:
    claves = [c for c in dict.fromkeys([*antes, *despues]) if antes.get(c) != despues.get(c)]
    return {c: antes.get(c) for c in claves}, {c: despues.get(c) for c in claves}
