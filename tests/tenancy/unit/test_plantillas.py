"""T4: plantillas de rol iniciales (RF-TEN-01; spec 0001c, "Plantillas de rol iniciales")."""

from shared.domain.accesos import CATALOGO, CORE, PERMISOS
from tenancy.domain.plantillas import PLANTILLAS, roles_iniciales


def test_las_plantillas_usan_permisos_del_catalogo():
    for permisos in PLANTILLAS.values():
        assert permisos <= set(PERMISOS)


def test_reproducen_la_tabla_de_la_spec():
    g, p, a, v = (PLANTILLAS[n] for n in ("Gerente", "Producción", "Almacén", "Ventas"))
    for rol in (g, p, a, v):
        assert {"core.dashboard.ver", "core.suscripcion.ver", "catalogo.producto.ver"} <= rol
        assert not rol & {"core.empresa.gestionar", "core.usuario.gestionar", "core.rol.gestionar"}
        assert not rol & {"catalogo.isc.gestionar", "facturacion.config.gestionar"}
    assert "catalogo.producto.gestionar" in g & p & a and "catalogo.producto.gestionar" not in v
    assert "inventario.costo.ver" in g & p & a and "inventario.costo.ver" not in v
    assert "inventario.stock.ver" in v and "inventario.kardex.ver" not in v
    assert {"inventario.ajuste.registrar", "inventario.ajuste.anular"} <= g
    assert "inventario.ajuste.registrar" in a and "inventario.ajuste.anular" not in a
    assert {"compras.compra.registrar", "compras.compra.anular"} <= g
    assert "compras.compra.registrar" in a and "compras.compra.anular" not in a
    assert "produccion.op.ejecutar" in p and "produccion.op.anular" not in p
    assert "produccion.op.anular" in g and not (a | v) & {"produccion.op.ver"}
    assert {"ventas.venta.registrar", "ventas.pedido.gestionar"} <= v & g
    assert "ventas.venta.anular" in g and "ventas.venta.anular" not in v
    assert "facturacion.comprobante.ver" in v and "facturacion.comprobante.gestionar" not in v
    assert {"finanzas.gasto.registrar", "finanzas.resultados.ver"} <= g
    assert not (p | a | v) & {"finanzas.resultados.ver"}
    assert "reportes.exportar" in g & p & a and "reportes.exportar" not in v


def test_se_recortan_a_las_funcionalidades_habilitadas():
    habilitadas = CORE | {"catalogo.productos", "ventas.clientes"}
    for nombre, permisos in roles_iniciales(habilitadas).items():
        assert {PERMISOS[p] for p in permisos} <= habilitadas, nombre
    assert set(roles_iniciales(set(CATALOGO))) == {"Gerente", "Producción", "Almacén", "Ventas"}
