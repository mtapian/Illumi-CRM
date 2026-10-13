"""Plantillas de rol iniciales (spec 0001c, "Plantillas de rol iniciales").

Se crean como roles editables al registrar la empresa, recortadas a lo habilitado.
Supuesto (la tabla no lo detalla): "stock y kardex" incluye lotes y, para Gerente y
Almacén, la gestión de almacenes; "Compras" incluye proveedores.
"""

from shared.domain.accesos import PERMISOS
from tenancy.domain.permisos import permisos_habilitados

_TODOS = {"core.dashboard.ver", "core.suscripcion.ver", "catalogo.producto.ver"}
_CATALOGO = {"catalogo.producto.gestionar", "catalogo.unidad.gestionar"}
_STOCK = {"inventario.stock.ver", "inventario.kardex.ver", "inventario.lote.ver"}
_COMPRAS = {"compras.proveedor.gestionar", "compras.compra.ver", "compras.compra.registrar"}
_PRODUCCION = {p for p in PERMISOS if p.startswith("produccion.")} - {"produccion.op.anular"}
_VENTAS = {
    "ventas.cliente.ver",
    "ventas.cliente.gestionar",
    "ventas.pedido.ver",
    "ventas.pedido.gestionar",
    "ventas.pedido.cancelar",
    "ventas.venta.ver",
    "ventas.venta.registrar",
    "ventas.cobranza.ver",
    "ventas.cobranza.gestionar",
}
_FINANZAS = {
    "finanzas.gasto.ver",
    "finanzas.gasto.registrar",
    "finanzas.gasto.anular",
    "finanzas.resultados.ver",
}

PLANTILLAS: dict[str, frozenset[str]] = {
    "Gerente": frozenset(
        _TODOS
        | _CATALOGO
        | _STOCK
        | {"inventario.costo.ver", "inventario.almacen.gestionar"}
        | {"inventario.ajuste.registrar", "inventario.ajuste.anular"}
        | _COMPRAS
        | {"compras.compra.anular"}
        | _PRODUCCION
        | {"produccion.op.anular"}
        | _VENTAS
        | {"ventas.venta.anular", "ventas.cobranza.anular", "ventas.metodo_pago.gestionar"}
        | {"facturacion.comprobante.ver", "facturacion.comprobante.gestionar"}
        | _FINANZAS
        | {"reportes.exportar"}
    ),
    "Producción": frozenset(
        _TODOS | _CATALOGO | _STOCK | {"inventario.costo.ver"} | _PRODUCCION | {"reportes.exportar"}
    ),
    "Almacén": frozenset(
        _TODOS
        | _CATALOGO
        | _STOCK
        | {"inventario.costo.ver", "inventario.almacen.gestionar", "inventario.ajuste.registrar"}
        | _COMPRAS
        | {"reportes.exportar"}
    ),
    "Ventas": frozenset(
        _TODOS | {"inventario.stock.ver"} | _VENTAS | {"facturacion.comprobante.ver"}
    ),
}


def roles_iniciales(habilitadas) -> dict[str, frozenset[str]]:
    habilitados = permisos_habilitados(habilitadas)
    return {nombre: permisos & habilitados for nombre, permisos in PLANTILLAS.items()}
