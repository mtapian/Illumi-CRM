"""Pasos de los escenarios de proveedores (spec 0002d)."""

from pytest_bdd import given, parsers, then, when

from purchasing.infrastructure.models import Proveedor, ProveedorProducto
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import como, re_
from tests.acceptance.pasos_catalogo import EMAIL, crear_directo, producto, tiene_pestana

PRECIO = r"(?P<precio>[\d.]+)"


def proveedor(ctx, nombre) -> Proveedor:
    return Proveedor.all_tenants.get(empresa=ctx["empresa"], razon_social=nombre)


@given(re_("el proveedor {} con RUC {}", "nombre", "numero"))
def existe_proveedor(ctx, nombre, numero):
    Proveedor.all_tenants.create(
        empresa=ctx["empresa"], tipo_doc="RUC", num_doc=numero, razon_social=nombre
    )


@given(re_("que {} tiene compras", "nombre"))
def tiene_compras(ctx, compras, nombre):
    compras.con_compras.add(proveedor(ctx, nombre).id)


@given(re_("que {} está desactivado", "nombre"))
def desactivado(ctx, nombre):
    Proveedor.all_tenants.filter(pk=proveedor(ctx, nombre).id).update(activo=False)


@given(re_("que existe el bien {} que no se compra", "sku"))
def bien_que_no_se_compra(ctx, sku):
    crear_directo(ctx, sku, u="L", se_compra=False, se_fabrica=True)


@when(
    parsers.re(
        r'registro el proveedor "(?P<nombre>[^"]+)" con (?P<tipo>RUC|DNI) "(?P<numero>[^"]+)"'
    )
)
def registro(client, ctx, nombre, tipo, numero):
    datos = {"accion": "guardar", "tipo_doc": tipo, "num_doc": numero, "razon_social": nombre}
    ctx["respuesta"] = como(client, EMAIL).post("/compras/proveedores/", datos, follow=True)


@then(re_("el proveedor {} queda activo", "nombre"))
def queda_activo(ctx, nombre):
    assert proveedor(ctx, nombre).activo


@when(re_("intento eliminar el proveedor {}", "nombre"))
def intento_eliminar(client, ctx, nombre):
    datos = {"accion": "eliminar", "id": proveedor(ctx, nombre).id}
    ctx["respuesta"] = como(client, EMAIL).post("/compras/proveedores/", datos, follow=True)


def _asociar(client, ctx, nombre, sku, precio, plazo):
    ctx["asociado"] = (nombre, sku, plazo)
    datos = {"proveedor": proveedor(ctx, nombre).id, "producto": producto(ctx, sku).id}
    datos |= {"precio": precio, "plazo": plazo}
    ctx["respuesta"] = como(client, EMAIL).post(
        "/compras/proveedores/producto/", datos, follow=True
    )


@when(
    parsers.re(
        r'asocio "(?P<nombre>[^"]+)" a "(?P<sku>[^"]+)" con precio '
        + PRECIO
        + r" y plazo (?P<plazo>\d+) días"
    )
)
def asocio(client, ctx, nombre, sku, precio, plazo):
    _asociar(client, ctx, nombre, sku, precio, plazo)


@when(parsers.re(r"lo vuelvo a asociar con precio " + PRECIO))
def vuelvo_a_asociar(client, ctx, precio):
    nombre, sku, plazo = ctx["asociado"]
    _asociar(client, ctx, nombre, sku, precio, plazo)


@then(
    parsers.re(
        r'la pestaña "Compras" de "(?P<sku>[^"]+)" muestra "(?P<nombre>[^"]+)" con precio '
        + PRECIO
        + r" y plazo (?P<plazo>\d+) días"
    )
)
def pestana_muestra(client, ctx, sku, nombre, precio, plazo):
    html = contenido(como(client, EMAIL).get(f"/catalogo/productos/{producto(ctx, sku).id}/"))
    assert tiene_pestana(html, "Compras")
    assert f"<td>{nombre}</td><td>{precio}</td><td>{plazo}</td>" in html


@then(
    parsers.re(
        r'"(?P<sku>[^"]+)" tiene un solo registro de "(?P<nombre>[^"]+)" con precio ' + PRECIO
    )
)
def un_solo_registro(ctx, sku, nombre, precio):
    filas = ProveedorProducto.all_tenants.filter(
        proveedor=proveedor(ctx, nombre), producto=producto(ctx, sku)
    )
    assert [str(f.precio_referencial) for f in filas] == [precio]


@then(re_("no veo la pestaña {}", "etiqueta"))
def no_veo_pestana(ctx, etiqueta):
    assert not tiene_pestana(ctx["ficha"], etiqueta)
