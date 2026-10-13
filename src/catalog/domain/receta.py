"""Receta de un bien que se fabrica: opcional, de uno o varios componentes, cualquier
producto activo del catálogo (spec 0002a, enmienda 4, RF-CAT-41). La orden de producción
copia sus componentes y los puede editar (0005a, RF-PRD-37)."""

from decimal import ROUND_HALF_UP, Decimal

from catalog.domain.errores import RecetaInvalida

CAMPO = "componente_0"  # el error se muestra en la receta (docs/ux.md §4)

CUATRO_DECIMALES = Decimal("0.0001")  # cantidades (RN-GEN-09)

Receta = tuple[tuple[int, Decimal], ...]  # (componente_id, cantidad por unidad)


def validar_receta(producto_id: int | None, componentes, estados: dict) -> None:
    """`estados`: componente_id → (tipo, activo). Una receta vacía es "sin receta"."""
    ids = [c for c, _ in componentes]
    if producto_id is not None and producto_id in ids:
        raise RecetaInvalida("Un producto no puede ser componente de sí mismo", CAMPO)
    if len(set(ids)) != len(ids):
        raise RecetaInvalida("Un componente está repetido en la receta", CAMPO)
    if any(c is None or c <= 0 for _, c in componentes):
        raise RecetaInvalida("La cantidad de cada componente debe ser mayor a 0", CAMPO)
    if any(not estados.get(i, (None, False))[1] for i in ids):
        raise RecetaInvalida("Un componente no existe o está inactivo", CAMPO)


def hay_ciclo(grafo: dict[int, set[int]], producto_id: int, componentes: set[int]) -> bool:
    """¿Usar `componentes` en la receta de `producto_id` crea un ciclo? `grafo`: producto →
    sus componentes actuales (la receta propia del producto se reemplaza, no se suma)."""
    pendientes, vistos = list(componentes), set()
    while pendientes:
        actual = pendientes.pop()
        if actual == producto_id:
            return True
        if actual not in vistos:
            vistos.add(actual)
            pendientes += grafo.get(actual, ()) if actual != producto_id else ()
    return False


def componentes_para(receta: Receta, cantidad: Decimal) -> dict[int, Decimal]:
    """Componente → cantidad para producir `cantidad` (4 decimales, half-up). La usa 0005a."""
    return {m: (c * cantidad).quantize(CUATRO_DECIMALES, ROUND_HALF_UP) for m, c in receta}


def contenido_sugerido(receta, unidades: dict[int, str]) -> Decimal | None:
    """Litros por unidad sugeridos desde la receta: suma de los componentes en L (informativo)."""
    litros = [q for c, q in receta if unidades.get(c) == "L"]
    return sum(litros, Decimal("0")).quantize(CUATRO_DECIMALES) if litros else None
