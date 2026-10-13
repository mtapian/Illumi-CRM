"""Catálogo de módulos, funcionalidades y permisos como código (spec 0001b, ADR-11).

Lo define el producto: el super admin lo empaqueta en planes y lo habilita por empresa,
pero no inventa permisos. Al cambiarlo, la tabla se sincroniza sola al migrar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Funcionalidad:
    codigo: str
    nombre: str
    modulo: str
    permisos: tuple[str, ...]
    requiere: tuple[str, ...] = ()


MODULOS = {
    "CORE": "Core",
    "CATALOGO": "Catálogo",
    "INVENTARIO": "Inventario",
    "COMPRAS": "Compras",
    "PRODUCCION": "Producción",
    "VENTAS": "Ventas",
    "FACTURACION": "Facturación",
    "FINANZAS": "Finanzas",
    "TRANSVERSAL": "Transversal",
}

_F = Funcionalidad
CATALOGO = {
    f.codigo: f
    for f in (
        _F(
            "core.admin",
            "Administración de empresa",
            "CORE",
            (
                "core.empresa.gestionar",
                "core.usuario.gestionar",
                "core.rol.gestionar",
                "core.auditoria.ver",
                "core.suscripcion.ver",
            ),
        ),
        _F("core.dashboard", "Dashboard", "CORE", ("core.dashboard.ver",)),
        _F(
            "catalogo.productos",
            "Productos y presentaciones",
            "CATALOGO",
            (
                "catalogo.producto.ver",
                "catalogo.producto.gestionar",
                "catalogo.unidad.gestionar",
                "catalogo.isc.gestionar",
            ),
        ),
        _F(
            "inventario.stock",
            "Stock y kardex",
            "INVENTARIO",
            ("inventario.stock.ver", "inventario.kardex.ver", "inventario.costo.ver"),
            ("catalogo.productos",),
        ),
        _F(
            "inventario.ajustes",
            "Ajustes de inventario",
            "INVENTARIO",
            ("inventario.ajuste.registrar", "inventario.ajuste.anular"),
            ("inventario.stock",),
        ),
        _F(
            "inventario.multialmacen",
            "Multialmacén",
            "INVENTARIO",
            ("inventario.almacen.gestionar",),
            ("inventario.stock",),
        ),
        _F(
            "inventario.lotes",
            "Lotes y vencimientos",
            "INVENTARIO",
            ("inventario.lote.ver",),
            ("inventario.stock",),
        ),
        _F(
            "compras.compras",
            "Compras y proveedores",
            "COMPRAS",
            (
                "compras.proveedor.gestionar",
                "compras.compra.ver",
                "compras.compra.registrar",
                "compras.compra.anular",
            ),
            ("inventario.stock",),
        ),
        _F(
            "produccion.op",
            "Órdenes de producción",
            "PRODUCCION",
            (
                "produccion.op.ver",
                "produccion.op.planificar",
                "produccion.op.ejecutar",
                "produccion.op.anular",
                "produccion.reporte.ver",
            ),
            # 0005a: la receta es del catálogo y el envasado es una OP (se retiran
            # "Recetas" y "Envasado multipresentación").
            ("inventario.stock",),
        ),
        _F(
            "ventas.clientes",
            "Clientes",
            "VENTAS",
            ("ventas.cliente.ver", "ventas.cliente.gestionar"),
            ("catalogo.productos",),
        ),
        _F(
            "ventas.pedidos",
            "Pedidos",
            "VENTAS",
            ("ventas.pedido.ver", "ventas.pedido.gestionar", "ventas.pedido.cancelar"),
            ("ventas.clientes", "inventario.stock"),
        ),
        _F(
            "ventas.ventas",
            "Ventas",
            "VENTAS",
            ("ventas.venta.ver", "ventas.venta.registrar", "ventas.venta.anular"),
            ("ventas.clientes", "inventario.stock"),
        ),
        _F(
            "facturacion.electronica",
            "Facturación electrónica",
            "FACTURACION",
            (
                "facturacion.config.gestionar",
                "facturacion.comprobante.ver",
                "facturacion.comprobante.gestionar",
            ),
            ("ventas.ventas",),
        ),
        _F(
            "finanzas.gastos",
            "Gastos",
            "FINANZAS",
            ("finanzas.gasto.ver", "finanzas.gasto.registrar", "finanzas.gasto.anular"),
        ),
        _F(
            "finanzas.resultados",
            "Estado de resultados",
            "FINANZAS",
            ("finanzas.resultados.ver",),
            ("ventas.ventas",),
        ),
        _F("transversal.exportacion", "Exportación CSV", "TRANSVERSAL", ("reportes.exportar",)),
        _F("transversal.api", "API de integración", "TRANSVERSAL", ("api.token.gestionar",)),
    )
}

# permiso → funcionalidad a la que pertenece
PERMISOS = {p: f.codigo for f in CATALOGO.values() for p in f.permisos}
CORE = frozenset(c for c, f in CATALOGO.items() if f.modulo == "CORE")
_ORDEN = {c: i for i, c in enumerate(CATALOGO)}


def funcionalidad(codigo: str) -> Funcionalidad:
    return CATALOGO[codigo]


def en_orden(codigos) -> list[str]:
    return sorted(codigos, key=_ORDEN.__getitem__)


def requeridas(codigo: str) -> set[str]:
    """Todas las funcionalidades que `codigo` necesita, directa o indirectamente."""
    pendientes, vistas = list(CATALOGO[codigo].requiere), set()
    while pendientes:
        c = pendientes.pop()
        if c not in vistas:
            vistas.add(c)
            pendientes.extend(CATALOGO[c].requiere)
    return vistas


def dependencias_faltantes(conjunto) -> list[str]:
    """Funcionalidades requeridas por las del conjunto que no están en él (RN-TEN-09)."""
    faltan = set().union(*(requeridas(c) for c in conjunto)) - set(conjunto) - CORE
    return en_orden(faltan)


def nombres(codigos) -> str:
    return ", ".join(CATALOGO[c].nombre for c in en_orden(codigos))
