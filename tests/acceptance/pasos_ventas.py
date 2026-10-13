"""Pasos de los escenarios de clientes y pedidos (spec 0006a)."""

import re
from datetime import date, timedelta
from decimal import Decimal as D

from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from sales.application import clientes as uc
from sales.application import pedidos as up
from sales.domain.cliente import DatosCliente
from sales.domain.pedido import LineaPedido, numero_pedido
from sales.infrastructure.contenedor import (
    buscar_clientes,
    caso_de_cliente,
    caso_de_pedido,
    sembrar_cliente_generico,
)
from sales.infrastructure.models import Cliente, Pedido
from sales.interfaces.views import disponibilidad
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_catalogo import ROLES, crear_directo, producto
from tests.acceptance.pasos_inventario import mover
from tests.acceptance.pasos_produccion import email

ROLES["ventas"] = "Ventas"
ESTADOS = {"Creado": "CREADO", "Aprobado": "APROBADO", "Cancelado": "CANCELADO"}


def intentar(ctx, accion):
    ctx["textos"] = []
    try:
        with tenant_context(ctx["empresa"].id):
            return accion()
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def hoy(ctx) -> date:
    return ctx.get("hoy") or timezone.localdate()


def cliente(ctx, nombre) -> Cliente:
    return Cliente.all_tenants.get(empresa=ctx["empresa"], nombre=nombre)


def pedido(ctx) -> Pedido:
    return Pedido.all_tenants.get(pk=ctx["pedido"])


# --- Antecedentes ---


@given(re_("el cliente {} con RUC {} y canal {}", "nombre", "ruc", "canal"))
def cliente_con_ruc(ctx, nombre, ruc, canal):
    sembrar_cliente_generico(ctx["empresa"].id, None, hoy(ctx))  # RF-VEN-03
    Cliente.all_tenants.create(
        empresa=ctx["empresa"], nombre=nombre, tipo_doc="RUC", num_doc=ruc, canal=canal
    )


@given("los productos que se venden con stock sin vencer:")
def productos_con_stock(ctx, datatable):
    for sku, precio, stock in datatable[1:]:
        crear_directo(
            ctx,
            sku,
            u="UND",
            se_compra=False,
            se_vende=True,
            se_fabrica=True,
            precio_venta=D(precio),
        )
        if D(stock) > 0:
            mover(ctx, "ENTRADA", "COMPRA", sku, stock, "4")


# --- Clientes ---


@when(
    parsers.re(
        r'creo el cliente "(?P<nombre>[^"]+)" con tipo "(?P<tipo>[^"]+)", '
        r'número "(?P<numero>[^"]*)" y email "(?P<correo>[^"]*)"'
    )
)
def creo_cliente(ctx, nombre, tipo, numero, correo):
    datos = DatosCliente(nombre, tipo, numero, email=correo)
    guardar = caso_de_cliente(uc.GuardarCliente)
    intentar(ctx, lambda: guardar.ejecutar(actor(email(ctx)), None, datos))


@then(re_("el resultado es {}", "resultado"))
def resultado(ctx, resultado):
    if resultado == "creado":
        assert not ctx["textos"], ctx["textos"]
    else:
        assert any(resultado in t for t in ctx["textos"]), ctx["textos"]


@then(re_("la empresa tiene el cliente {} sin documento", "nombre"))
def tiene_generico(ctx, nombre):
    c = cliente(ctx, nombre)
    assert (c.tipo_doc, c.num_doc, c.es_generico) == ("SD", "", True)


@when(re_("intento desactivar el cliente {}", "nombre"))
def intento_desactivar(ctx, nombre):
    id_ = cliente(ctx, nombre).id
    intentar(
        ctx,
        lambda: caso_de_cliente(uc.CambiarEstadoCliente).ejecutar(actor(email(ctx)), id_, False),
    )


@when(re_("desactivo el cliente {}", "nombre"))
def desactivo(ctx, nombre):
    intento_desactivar(ctx, nombre)
    assert not ctx["textos"], ctx["textos"]


@then(re_("{} no se ofrece en un pedido nuevo", "nombre"))
def no_se_ofrece(ctx, nombre):
    assert nombre not in [c.nombre for c in buscar_clientes(ctx["empresa"].id, nombre)]


@then(re_("el pedido de {} conserva su cliente", "nombre"))
def conserva_cliente(ctx, nombre):
    assert pedido(ctx).cliente.nombre == nombre


@when(re_("busco el cliente {} en un pedido nuevo", "texto"))
def busco(ctx, texto):
    ctx["encontrados"] = [c.nombre for c in buscar_clientes(ctx["empresa"].id, texto)]


@then(re_("encuentro {}", "nombre"))
def encuentro(ctx, nombre):
    assert nombre in ctx["encontrados"]


@then("no encuentro clientes")
def no_encuentro(ctx):
    assert ctx["encontrados"] == []


@when(re_(r"registro al vuelo el cliente {} con DNI {} y teléfono {}", "nombre", "dni", "telefono"))
def registro_al_vuelo(client, ctx, nombre, dni, telefono):
    datos = {"nombre": nombre, "tipo_doc": "DNI", "num_doc": dni, "telefono": telefono}
    ctx["respuesta_rapida"] = como(client, email(ctx)).post("/ventas/clientes/rapido/", datos)


@then(re_("el pedido nuevo tiene elegido a {}", "nombre"))
def elegido(ctx, nombre):
    r = ctx["respuesta_rapida"]
    assert r.status_code == 200 and r.json()["nombre"] == nombre
    assert cliente(ctx, nombre).telefono == "987654321"


# --- Pedidos ---


def crear_pedido(ctx, nombre, lineas, fecha=None):
    filas = tuple(
        LineaPedido(producto(ctx, sku).id, D(q), producto(ctx, sku).precio_venta)
        for sku, q in lineas
    )
    datos = up.DatosPedido(
        cliente(ctx, nombre).id, fecha or hoy(ctx) + timedelta(days=5), "", filas
    )
    ctx["pedido"] = intentar(
        ctx, lambda: caso_de_pedido(up.CrearPedido).ejecutar(actor(email(ctx)), datos)
    )
    assert not ctx["textos"], ctx["textos"]


def aprobar(ctx):
    intentar(
        ctx,
        lambda: caso_de_pedido(up.AprobarPedido).ejecutar(
            actor(email(ctx)), ctx["pedido"], hoy(ctx)
        ),
    )


@given(
    parsers.re(
        r'un pedido(?P<aprobado> aprobado)? de "(?P<nombre>[^"]+)"'
        r'(?: para el "(?P<fecha>[^"]+)")? con (?P<n>[\d.]+) "(?P<sku>[^"]+)"'
    )
)
def un_pedido(ctx, aprobado, nombre, fecha, n, sku):
    crear_pedido(ctx, nombre, [(sku, n)], date.fromisoformat(fecha) if fecha else None)
    if aprobado:
        aprobar(ctx)
        assert not ctx["textos"], ctx["textos"]


@when(re_(r"creo un pedido de {} para el {} con:", "nombre", "fecha"))
def creo_pedido(ctx, nombre, fecha, datatable):
    crear_pedido(ctx, nombre, [tuple(f) for f in datatable[1:]], date.fromisoformat(fecha))


@then(re_(r"el pedido {} queda {} con total (?P<total>[\d.]+)", "numero", "estado"))
def pedido_con_total(ctx, numero, estado, total):
    p = pedido(ctx)
    assert (numero_pedido(p.numero), p.estado, p.total) == (numero, ESTADOS[estado], D(total))


@then("sus líneas muestran:")
def lineas_muestran(ctx, datatable):
    with tenant_context(ctx["empresa"].id):
        filas = disponibilidad([pedido(ctx)], hoy(ctx))[ctx["pedido"]]["lineas"]
    vistos = [
        (
            f["linea"].producto.sku,
            f"{f['linea'].precio:.2f}",
            str(f["disponible"].normalize()),
            str(f["faltante"].normalize()),
            "Quiebre de stock" if f["faltante"] else "",
        )
        for f in filas
    ]
    assert vistos == [tuple(f) for f in datatable[1:]]


@when("apruebo el pedido")
def apruebo(ctx):
    aprobar(ctx)


@then(re_("el pedido queda {}", "estado"))
def pedido_queda(ctx, estado):
    assert pedido(ctx).estado == ESTADOS[estado]


@when(re_(r"intento cambiar la cantidad de {} a (?P<n>[\d.]+)", "sku"))
def cambio_cantidad(ctx, sku, n):
    p = pedido(ctx)
    lineas = (LineaPedido(producto(ctx, sku).id, D(n), producto(ctx, sku).precio_venta),)
    datos = up.DatosPedido(p.cliente_id, p.fecha_entrega, p.comentario, lineas)
    intentar(ctx, lambda: caso_de_pedido(up.EditarPedido).ejecutar(actor(email(ctx)), p.id, datos))


@when("abro el listado de pedidos")
def abro_listado(ctx):
    with tenant_context(ctx["empresa"].id):
        pedidos = list(Pedido.objects.order_by("numero"))
        info = disponibilidad(pedidos, hoy(ctx))
    ctx["indicadores"] = {numero_pedido(p.numero): info[p.id]["indicadores"] for p in pedidos}


@then("veo los indicadores:")
def veo_indicadores(ctx, datatable):
    for numero, texto in datatable[1:]:
        assert ctx["indicadores"][numero] == [i.strip() for i in texto.split(",")], numero


@when("abro el inicio")
def abro_inicio(client, ctx):
    ctx["pagina"] = contenido(como(client, email(ctx)).get("/dashboard/"))


@then(re_("veo la alerta {}", "texto"))
def veo_alerta(ctx, texto):
    assert texto in ctx["pagina"]


@then(re_("la alerta lleva al listado de pedidos filtrado por {}", "filtro"))
def alerta_filtrada(ctx, filtro):
    assert filtro == "solo con quiebre de stock" and "/ventas/pedidos/?quiebre=1" in ctx["pagina"]


@when(re_(r"abro los pedidos en la vista {} con el filtro {}", "vista", "filtro"))
def abro_kanban(client, ctx, vista, filtro):
    parametros = {"vista": vista.lower()}
    if filtro == "solo con quiebre de stock":
        parametros["quiebre"] = "1"
    ctx["pagina"] = contenido(como(client, email(ctx)).get("/ventas/pedidos/", parametros))


def columnas(pagina) -> dict[str, list[str]]:
    resultado = {}
    for estado, cuerpo in re.findall(r'data-estado="(\w+)">(.*?)</section>', pagina, re.S):
        resultado[estado] = re.findall(r'data-pedido="([^"]+)"', cuerpo)
    return resultado


@then(re_("la columna {} tiene {}", "columna", "numero"))
def columna_tiene(ctx, columna, numero):
    assert numero in columnas(ctx["pagina"])[ESTADOS[columna]]


@then(re_("ninguna columna tiene {} ni {}", "a", "b"))
def ninguna_tiene(ctx, a, b):
    todos = [n for lista in columnas(ctx["pagina"]).values() for n in lista]
    assert a not in todos and b not in todos


@when("intento cancelar el pedido")
def intento_cancelar(ctx):
    intentar(
        ctx,
        lambda: caso_de_pedido(up.CancelarPedido).ejecutar(actor(email(ctx)), ctx["pedido"], "x"),
    )


@when(re_("cancelo el pedido con el motivo {}", "motivo"))
def cancelo(ctx, motivo):
    intentar(
        ctx,
        lambda: caso_de_pedido(up.CancelarPedido).ejecutar(
            actor(email(ctx)), ctx["pedido"], motivo
        ),
    )
    assert not ctx["textos"], ctx["textos"]
