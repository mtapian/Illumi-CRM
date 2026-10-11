"""Pasos de los escenarios de compras (spec 0004a). Usan los casos de uso, como los de ajustes;
"registro una compra" es crearla y finalizarla."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D

from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from inventory.infrastructure.models import CostoProducto, Lote, Movimiento, Stock
from purchasing.application import compras as uc
from purchasing.application.compras import DatosCompra
from purchasing.domain.compra import LineaCompra
from purchasing.infrastructure.contenedor import caso_de_compra
from purchasing.infrastructure.models import Compra, Proveedor
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import tenancy_service
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_catalogo import EMAIL, crear_directo, producto, soy_usuario
from tests.acceptance.pasos_inventario import almacen, mover
from tests.acceptance.pasos_proveedores import proveedor

DOC = {"factura": "FACTURA", "boleta": "BOLETA"}
PROV = r'"(?P<prov>[^"]+)"'


def dia(texto: str) -> date:
    hoy = date.today()
    return {"hoy": hoy, "mañana": hoy + timedelta(days=1)}.get(texto) or hoy - timedelta(
        days=int(texto.split()[1])
    )


def intentar(ctx, hacer):
    """Un error de negocio queda para el paso "rechazada"."""
    try:
        with tenant_context(ctx["empresa"].id):
            return hacer()
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def linea(ctx, fila: dict) -> LineaCompra:
    vence = fila.get("vence")
    return LineaCompra(
        producto(ctx, fila["producto"]).id,
        D(fila["cantidad"]),
        D(fila["costo_unitario"]),
        fila.get("bonificacion") == "sí",
        fila.get("lote") or None,
        vence and date.fromisoformat(vence),
    )


def crear(ctx, filas, prov="Maltería del Sur", doc="BOLETA", serie=None, alm="Principal", **kw):
    ctx["n_doc"] = ctx.get("n_doc", 0) + 1
    datos = DatosCompra(
        proveedor(ctx, prov).id,
        kw.get("fecha", date.today()),
        almacen(ctx, alm),
        doc,
        serie or f"B900-{ctx['n_doc']}",
        lineas=[linea(ctx, f) for f in filas],
    )
    ctx.pop("textos", None)
    ctx["datos"] = datos
    ctx["compra"] = intentar(
        ctx, lambda: caso_de_compra(uc.CrearCompra).ejecutar(actor(EMAIL), datos)
    )
    return ctx["compra"]


def finalizar(ctx, alm=None, recepcion="hoy", guia=""):
    def hacer():
        compra = Compra.objects.get(pk=ctx["compra"])
        destino = almacen(ctx, alm) if alm else compra.almacen_id
        caso = caso_de_compra(uc.FinalizarCompra)
        caso.ejecutar(actor(EMAIL), compra.id, destino, dia(recepcion), guia, date.today())

    intentar(ctx, hacer)


def registrar(ctx, filas, **kw):
    if crear(ctx, filas, **kw):
        finalizar(ctx)


def tabla(datatable) -> list[dict]:
    return [dict(zip(datatable[0], fila, strict=True)) for fila in datatable[1:]]


def compra(ctx, numero=None) -> Compra:
    filas = Compra.all_tenants.filter(empresa=ctx["empresa"])
    return filas.get(numero=int(numero[2:])) if numero else filas.get(pk=ctx["compra"])


def entrada(ctx, sku) -> Movimiento:
    return Movimiento.all_tenants.get(
        producto=producto(ctx, sku), ref_tipo="COMPRA", ref_id=ctx["compra"]
    )


def malta(cantidad="1", costo="5", **kw):
    return {"producto": "INS-MALTA", "cantidad": cantidad, "costo_unitario": costo} | kw


# --- Antecedentes ---


@given(re_(r"que soy usuario {} de {} con IGV (?P<igv>\d+) %", "rol", "nombre"))
def soy_usuario_con_igv(client, ctx, inventario, rol, nombre, igv):
    soy_usuario(client, ctx, inventario, rol, nombre)
    with tenant_context(ctx["empresa"].id):
        assert tenancy_service().igv_vigente(date.today()) == D(igv)


@given(
    re_(r"el bien que se compra {} con stock (?P<n>\d+) KG y costo promedio (?P<p>[\d.]+)", "sku")
)
def bien_con_stock(ctx, sku, n, p):
    crear_directo(ctx, sku)
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, n, p)


@given(re_("el bien que se compra {} sin stock", "sku"))
def bien_sin_stock(ctx, sku):
    crear_directo(ctx, sku, u="UND")


@given(re_("el (?P<tipo>bien|servicio) {} que no se compra", "sku"))
def no_se_compra(ctx, tipo, sku):
    if tipo == "bien":
        crear_directo(ctx, sku, se_compra=False, se_fabrica=True)
    else:
        crear_directo(
            ctx, sku, u="SERV", tipo="SERVICIO", se_compra=False, se_vende=True, precio_venta=30
        )


@given(re_(r"el bien {} que se compra y se vende(?:, con vida útil de (?P<dias>\d+) días)?", "sku"))
def se_compra_y_vende(ctx, sku, dias):
    vida = {"vida_util_dias": int(dias)} if dias else {}
    crear_directo(ctx, sku, u="UND", se_vende=True, precio_venta=2, **vida)


@given(re_(r"el proveedor {} con DNI {}", "nombre", "numero"))
def proveedor_con_dni(ctx, nombre, numero):
    Proveedor.all_tenants.create(
        empresa=ctx["empresa"], tipo_doc="DNI", num_doc=numero, razon_social=nombre
    )


@given(re_(r"el lote {} de {}(?: con (?P<n>\d+) UND)? que vence el {}", "lote", "sku", "vence"))
def lote_existente(ctx, lote, sku, n, vence):
    crear_directo(ctx, sku, u="UND", se_vende=True, precio_venta=2)
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, n or "1", "1", lote, date.fromisoformat(vence))


@given(re_(r"una compra registrada a {} con factura {}", "prov", "serie"))
def compra_registrada(ctx, prov, serie):
    registrar(ctx, [malta()], prov=prov, doc="FACTURA", serie=serie)


@given(re_("el almacén {} activo", "nombre"))
def almacen_activo(ctx, nombre):
    almacen(ctx, nombre)


@given(
    re_(
        r"una compra {} a {} de (?P<n>\d+) KG de {}(?: con lote {})?(?: con almacén {})?",
        "estado",
        "prov",
        "sku",
        "lote",
        "alm",
    )
)
def compra_en_estado(ctx, estado, prov, n, sku, lote, alm):
    crear(ctx, [malta(n, lote=lote)], prov=prov, alm=alm or "Principal")
    if estado == "EN_PROCESO":
        intentar(
            ctx, lambda: caso_de_compra(uc.PasarAEnProceso).ejecutar(actor(EMAIL), ctx["compra"])
        )


# --- Registrar ---


@when(
    parsers.re(
        r"registro (?:una|otra) compra a "
        + PROV
        + r' con (?P<doc>factura|boleta) "(?P<serie>[^"]+)"(?: al almacén "(?P<alm>[^"]+)")?:?'
    )
)
def registro_compra(ctx, prov, doc, serie, alm, datatable=None):
    filas = tabla(datatable) if datatable else [malta()]
    registrar(ctx, filas, prov=prov, doc=DOC[doc], serie=serie, alm=alm or "Principal")


@when(re_("registro una compra con el producto {}", "sku"))
def registro_con_producto(ctx, sku):
    registrar(ctx, [{"producto": sku, "cantidad": "1", "costo_unitario": "1"}])


@when(re_("registro una compra con {} igual a {}", "campo", "valor"))
def registro_con_campo(ctx, campo, valor):
    registrar(ctx, [] if campo == "lineas" else [malta() | {campo: valor}])


@when(
    re_(
        r"registro una compra de (?P<n>\d+) UND de {}"
        r"(?: sin lote| al lote {} sin vencimiento| al lote {} con vencimiento {})",
        "sku",
        "lote",
        "lote2",
        "vence",
    )
)
def registro_con_lote(ctx, n, sku, lote, lote2, vence):
    fila = {"producto": sku, "cantidad": n, "costo_unitario": "1.20"}
    registrar(ctx, [fila | {"lote": lote or lote2, "vence": vence}])


@when(
    re_(
        r"creo una compra a {} con factura {} de (?P<n>\d+) KG de {} a (?P<c>[\d.]+)",
        "prov",
        "serie",
        "sku",
    )
)
def creo_compra(ctx, prov, serie, n, sku, c):
    crear(ctx, [malta(n, c)], prov=prov, doc="FACTURA", serie=serie)


@when(re_("creo una compra a {} con fecha {}", "prov", "fecha"))
def creo_con_fecha(ctx, prov, fecha):
    crear(ctx, [malta()], prov=prov, fecha=dia(fecha))


@when(re_(r"cambio la cantidad a (?P<n>\d+) KG y la paso a {}", "estado"))
def cambio_y_paso(ctx, n, estado):
    datos = replace(ctx["datos"], lineas=[replace(ctx["datos"].lineas[0], cantidad=D(n))])

    def hacer():
        caso_de_compra(uc.EditarCompra).ejecutar(actor(EMAIL), ctx["compra"], datos)
        caso_de_compra(uc.PasarAEnProceso).ejecutar(actor(EMAIL), ctx["compra"])

    intentar(ctx, hacer)


@when("finalizo la compra")
def finalizo(ctx):
    finalizar(ctx)


@when(re_("finalizo la compra con fecha de recepción {}", "fecha"))
def finalizo_con_fecha(ctx, fecha):
    finalizar(ctx, recepcion=fecha)


@when(
    re_(
        "finalizo la compra con almacén {}, fecha de recepción {} y guía {}", "alm", "fecha", "guia"
    )
)
def finalizo_con_todo(ctx, alm, fecha, guia):
    ctx["finalizada"] = ctx["compra"]
    finalizar(ctx, alm, fecha, guia)


@when(re_("intento finalizar otra compra con (?:fecha de recepción {}|guía {})", "fecha", "guia"))
def intento_finalizar_otra(ctx, fecha, guia):
    crear(ctx, [malta()])
    finalizar(ctx, recepcion=fecha or "hoy", guia=guia or "")


# --- Verificaciones ---


@then(re_("la compra {} queda {} con:", "numero", "estado"))
def queda_con(ctx, numero, estado, datatable):
    c = compra(ctx, numero)
    [esperado] = tabla(datatable)
    assert c.estado == estado
    assert {k: str(getattr(c, k)) for k in esperado} == esperado


@then(re_(r"la compra queda {}(?: con subtotal (?P<s>[\d.]+)| con fecha {})?", "estado", "fecha"))
def queda(ctx, estado, s, fecha):
    c = compra(ctx)
    assert c.estado == estado
    assert s is None or c.subtotal == D(s)
    assert fecha is None or c.fecha == dia(fecha)


@then(re_(r"la compra queda {} y {} (?:sigue con|tiene) stock (?P<n>\d+) KG", "estado", "sku"))
def queda_y_stock(ctx, estado, sku, n):
    assert compra(ctx).estado == estado
    assert CostoProducto.all_tenants.get(producto=producto(ctx, sku)).cantidad_total == D(n)


@then("la compra ya no se puede editar")
def no_se_edita(ctx):
    caso = caso_de_compra(uc.EditarCompra)
    intentar(ctx, lambda: caso.ejecutar(actor(EMAIL), ctx["compra"], ctx["datos"]))
    assert ctx["textos"] == ["La compra ya está finalizada"]


@then(
    re_("el kardex de ambos productos tiene una entrada {} que referencia {}", "motivo", "numero")
)
def kardex_referencia(ctx, motivo, numero):
    c = compra(ctx, numero)
    movs = Movimiento.all_tenants.filter(ref_tipo="COMPRA", ref_id=c.id)
    assert sorted(m.producto.sku for m in movs if m.motivo == motivo) == ["ENV-BOT330", "INS-MALTA"]


@then(re_(r"la compra tiene IGV (?P<igv>[\d.]+) y total (?P<total>[\d.]+)"))
def igv_y_total(ctx, igv, total):
    c = compra(ctx)
    assert (c.igv, c.total) == (D(igv), D(total))


@then(
    re_(
        r"la entrada de {} es(?: de (?P<n>\d+) UND al lote {})? a costo (?P<c>[\d.]+)",
        "sku",
        "lote",
    )
)
def entrada_a_costo(ctx, sku, n, lote, c):
    m = entrada(ctx, sku)
    assert m.costo_unitario == D(c)
    assert n is None or (m.cantidad, m.lote.codigo) == (D(n), lote)


@then(re_("el lote {} vence el {} y queda disponible para venta FEFO", "lote", "vence"))
def lote_disponible(ctx, lote, vence):
    s = Stock.all_tenants.get(empresa=ctx["empresa"], lote__codigo=lote)
    assert s.lote.fecha_vencimiento == date.fromisoformat(vence) >= date.today()
    assert s.cantidad > 0


@then(re_(r"{} tiene (?P<n>\d+) UND sin lote", "sku"))
def sin_lote(ctx, sku, n):
    assert Stock.all_tenants.get(producto=producto(ctx, sku), lote=None).cantidad == D(n)


@then(re_(r"el lote {} vence a los (?P<dias>\d+) días de la fecha de recepción", "lote"))
def vence_desde_recepcion(ctx, lote, dias):
    fila = Lote.all_tenants.get(empresa=ctx["empresa"], codigo=lote)
    assert fila.fecha_ingreso == compra(ctx).fecha_recepcion
    assert fila.fecha_vencimiento == fila.fecha_ingreso + timedelta(days=int(dias))


@then(re_(r"el lote {} queda con (?P<n>\d+) UND", "lote"))
def lote_con(ctx, lote, n):
    assert Stock.all_tenants.get(empresa=ctx["empresa"], lote__codigo=lote).cantidad == D(n)


@then(
    re_(
        r"{} queda con stock (?P<n>\d+) KG, valor (?P<v>[\d.]+) y costo promedio (?P<p>[\d.]+)",
        "sku",
    )
)
def queda_valorizado(ctx, sku, n, v, p):
    c = CostoProducto.all_tenants.get(producto=producto(ctx, sku))
    assert (c.cantidad_total, c.valor_total, c.costo_promedio) == (D(n), D(v), D(p))


@then("el movimiento de kardex tiene la fecha de hoy")
def kardex_hoy(ctx):
    [m] = Movimiento.all_tenants.filter(ref_tipo="COMPRA", ref_id=ctx["compra"])
    assert timezone.localtime(m.fecha).date() == date.today()


@then(
    re_("el movimiento de kardex y el ingreso del lote {} tienen la fecha de (?P<fecha>.+)", "lote")
)
def kardex_y_lote(ctx, lote, fecha):
    [m] = Movimiento.all_tenants.filter(ref_tipo="COMPRA", ref_id=ctx["compra"])
    assert timezone.localtime(m.fecha).date() == dia(fecha) == m.lote.fecha_ingreso
    assert m.lote.codigo == lote


@then(
    re_(r"{} tiene stock (?P<a>\d+) KG en {} y sigue con (?P<b>\d+) KG en {}", "sku", "alm", "alm2")
)
def stock_por_almacen(ctx, sku, a, alm, b, alm2):
    def en(nombre):
        filas = Stock.all_tenants.filter(producto=producto(ctx, sku), almacen__nombre=nombre)
        return sum((s.cantidad for s in filas), D("0"))

    assert (en(alm), en(alm2)) == (D(a), D(b))


@then(re_("la compra muestra el almacén {} y la guía {}", "alm", "guia"))
def muestra(client, ctx, alm, guia):
    html = contenido(como(client, EMAIL).get(f"/compras/{ctx['finalizada']}/"))
    assert alm in html and guia in html
