"""Pasos de los escenarios de inventario (specs 0003a y 0003b). Los ajustes usan su caso de
uso; las compras (0004a) y las OP (0005a) aún no existen: esos pasos llaman directo al
servicio de inventario con el motivo que esas specs usarán."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import DatabaseError, transaction
from pytest_bdd import given, parsers, then, when

from inventory.application import ajustes as ua
from inventory.application.ajustes import LineaAjuste
from inventory.application.servicio import InventarioService, Linea
from inventory.infrastructure.contenedor import caso_de_ajuste, inventario
from inventory.infrastructure.models import (
    Ajuste,
    AjusteLinea,
    Almacen,
    CostoProducto,
    Lote,
    Movimiento,
    Stock,
)
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import Usuario
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_catalogo import EMAIL, ROLES, crear_directo, producto
from tests.acceptance.pasos_sesion import crear_usuario

REF = {"COMPRA": "COMPRA", "CONSUMO_OP": "OP", "VENTA": "VENTA"}  # el resto, AJUSTE
OPERACION = r'(?P<cant>[\d.]+) (?P<u>\w+) de "(?P<sku>[^"]+)"'


def hoy(ctx) -> date:
    return ctx.get("hoy") or date.today()


def almacen(ctx, nombre="Principal") -> int:
    return Almacen.all_tenants.get_or_create(empresa=ctx["empresa"], nombre=nombre)[0].id


def mover(ctx, tipo, motivo, sku, cant, costo=None, lote=None, vence=None, alm="Principal"):
    """Registra la operación; un error de negocio queda para el paso "rechazada"."""
    linea = Linea(
        producto(ctx, sku).id, almacen(ctx, alm), D(cant), costo and D(costo), lote, vence
    )
    ctx["n_ref"] = ctx.get("n_ref", 0) + 1
    try:
        with tenant_context(ctx["empresa"].id), transaction.atomic():
            servicio = inventario()
            registrar = {
                "ENTRADA": servicio.registrar_entrada,
                "SALIDA": servicio.registrar_salida,
            }[tipo]
            ctx["ids"] = registrar(
                motivo, REF.get(motivo, "AJUSTE"), ctx["n_ref"], [linea], None, hoy(ctx)
            )
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def ajustar(ctx, tipo, lineas, motivo="Ajuste", alm="Principal", destino=None, email=EMAIL):
    """Registra un ajuste con su caso de uso (0003b); el error queda para "rechazada"."""
    try:
        with tenant_context(ctx["empresa"].id):
            ctx["ajuste"] = caso_de_ajuste(ua.RegistrarAjuste).ejecutar(
                actor(email),
                tipo,
                almacen(ctx, alm),
                motivo,
                lineas,
                destino and almacen(ctx, destino),
                hoy(ctx),
            )
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def bien(ctx, sku, u="KG") -> int:
    ctx["sku"] = sku
    return crear_directo(ctx, sku, u=u).id


def movimientos(ctx, sku):
    return Movimiento.all_tenants.filter(producto=producto(ctx, sku)).order_by("id")


def costo(ctx, sku) -> CostoProducto:
    return CostoProducto.all_tenants.get(producto=producto(ctx, sku))


# --- Antecedentes ---


@given(re_("la fecha de hoy es {}", "fecha"))
def fecha_de_hoy(ctx, fecha):
    ctx["hoy"] = date.fromisoformat(fecha)


@given(re_("existe el bien {} que se compra, en KG, sin stock", "sku"))
def bien_que_se_compra(ctx, sku):
    crear_directo(ctx, sku)
    ctx["sku"] = sku


@given(re_("el almacén {}", "nombre"))
def el_almacen(ctx, nombre):
    almacen(ctx, nombre)


@given(re_("el bien {} que se fabrica y se vende, con stock por lote en {}:", "sku", "alm"))
def bien_con_lotes(ctx, sku, alm, datatable):
    crear_directo(
        ctx, sku, u="UND", se_compra=False, se_fabrica=True, se_vende=True, precio_venta=12
    )
    ctx["sku"] = sku
    for codigo, vence, cant in datatable[1:]:
        mover(
            ctx, "ENTRADA", "SALDO_INICIAL", sku, cant, "4", codigo, date.fromisoformat(vence), alm
        )


# --- Costo promedio y kardex ---


@when(
    parsers.re(
        r'registro un ajuste "SALDO_INICIAL" de '
        + OPERACION
        + r"(?: a costo (?P<c>[\d.]+)| sin costo unitario)"
        + r'(?: con lote "(?P<lote>[^"]+)" que vence el "(?P<vence>[^"]+)")?'
    )
)
def saldo_inicial(ctx, cant, u, sku, c, lote, vence):
    vence = vence and date.fromisoformat(vence)
    linea = LineaAjuste(bien(ctx, sku, u), D(cant), c and D(c), lote, vence)
    ajustar(ctx, "SALDO_INICIAL", [linea])


@when(parsers.re(r"se registra una compra de " + OPERACION + r" a costo (?P<c>[\d.]+)"))
def compra(ctx, cant, u, sku, c):
    mover(ctx, "ENTRADA", "COMPRA", sku, cant, c)


@when(parsers.re(r"se registra una compra de (?P<cant>[\d.]+) (?P<u>\w+) a costo (?P<c>[\d.]+)"))
def compra_del_mismo(ctx, cant, u, c):
    mover(ctx, "ENTRADA", "COMPRA", ctx["sku"], cant, c)


@when(parsers.re(r"se consumen " + OPERACION + r" en una OP"))
def consumo_op(ctx, cant, u, sku):
    mover(ctx, "SALIDA", "CONSUMO_OP", sku, cant)


@when(
    parsers.re(
        r'registro un ajuste "(?P<tipo>MERMA|CORRECCION)"(?P<salida> de salida)? de '
        + OPERACION
        + r'(?: del lote "(?P<lote>[^"]+)")?'
        + r'(?: con motivo "(?P<motivo>[^"]+)"|(?P<sin> sin motivo))?'
    )
)
def ajuste_de_salida(ctx, tipo, salida, cant, u, sku, lote, motivo, sin):
    sentido = "SALIDA" if tipo == "CORRECCION" else ""
    linea = LineaAjuste(bien(ctx, sku, u), D(cant), lote=lote, sentido=sentido)
    ajustar(ctx, tipo, [linea], "" if sin else motivo or "Ajuste")


@then(parsers.re(r'el kardex de "(?P<sku>[^"]+)" muestra:'))
def kardex(ctx, sku, datatable):
    campos = ("motivo", "tipo", "cantidad", "costo_unitario", "costo_total")
    campos += ("saldo_cantidad", "saldo_promedio")
    filas = [[str(getattr(m, c)) for c in campos] for m in movimientos(ctx, sku)]
    assert filas == datatable[1:]


@then(re_(r"el stock de {} es (?P<n>[\d.]+) (?P<u>\w+) valorizado en (?P<v>[\d.]+)", "sku"))
def stock_valorizado(ctx, sku, n, u, v):
    c = costo(ctx, sku)
    assert (c.cantidad_total, c.valor_total) == (D(n), D(v))


@given(re_(r"que {} tuvo stock y quedó en 0 con promedio (?P<p>[\d.]+)", "sku"))
def quedo_en_cero(ctx, sku, p):
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, "100", "4")
    mover(ctx, "ENTRADA", "COMPRA", sku, "50", "5")
    mover(ctx, "SALIDA", "CONSUMO_OP", sku, "150")
    assert (costo(ctx, sku).cantidad_total, costo(ctx, sku).costo_promedio) == (0, D(p))


@then(re_(r"el costo promedio de {} es (?P<p>[\d.]+)", "sku"))
def costo_promedio(ctx, sku, p):
    assert costo(ctx, sku).costo_promedio == D(p)


@given(re_(r"que {} tiene stock (?P<n>[\d.]+) (?P<u>\w+) en {}", "sku", "alm"))
def tiene_stock_en(ctx, sku, n, u, alm):
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, n, "4", alm=alm)
    ctx["n_movimientos"] = movimientos(ctx, sku).count()


@then("no se registra ningún movimiento")
def ningun_movimiento(ctx):
    assert movimientos(ctx, ctx["sku"]).count() == ctx["n_movimientos"]


# --- Concurrencia: corre con transacciones reales (ver test_e03a.py) ---


@when(re_(r"dos usuarios registran simultáneamente salidas de (?P<n>[\d.]+) KG de {}", "sku"))
def dos_salidas(ctx, n, sku):
    import threading

    from django.db import connection

    barrera, ctx["resultados"] = threading.Barrier(2), []
    linea = Linea(producto(ctx, sku).id, almacen(ctx), D(n))

    def salida():
        try:
            with tenant_context(ctx["empresa"].id), transaction.atomic():
                barrera.wait(timeout=5)
                inventario().registrar_salida("MERMA", "AJUSTE", 99, [linea], None, hoy(ctx))
            ctx["resultados"].append("ok")
        except DomainError as e:
            ctx["resultados"].append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=salida) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)


@then("exactamente una operación tiene éxito")
def una_con_exito(ctx):
    assert ctx["resultados"].count("ok") == 1


@then(re_("la otra es rechazada con {}", "mensaje"))
def la_otra(ctx, mensaje):
    assert any(mensaje in r for r in ctx["resultados"] if r != "ok")


@then(re_(r"el stock final es (?P<n>[\d.]+) KG"))
def stock_final(ctx, n):
    assert costo(ctx, ctx["sku"]).cantidad_total == D(n)


# --- Kardex inmutable ---


@given(re_("un movimiento registrado de {}", "sku"))
def un_movimiento(ctx, sku):
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, "10", "4")
    ctx["movimiento"] = movimientos(ctx, sku).last().id


@when("cualquier usuario intenta editarlo o eliminarlo")
def intenta_editar(ctx):
    # No hay pantalla, ruta ni operación del servicio que edite o borre movimientos.
    ctx["operaciones"] = [n for n in dir(InventarioService) if not n.startswith("_")]


@then("la operación no está disponible")
def no_disponible(ctx):
    prohibidas = ("editar", "modificar", "eliminar", "borrar", "actualizar")
    assert ctx["operaciones"]
    assert not [o for o in ctx["operaciones"] if o.startswith(prohibidas)]


@then("un intento directo en la base de datos es rechazado")
def directo_rechazado(ctx):
    for intento in (
        lambda q: q.update(cantidad=D("1")),
        lambda q: q.delete(),
    ):
        with transaction.atomic(), pytest.raises(DatabaseError):
            intento(Movimiento.all_tenants.filter(pk=ctx["movimiento"]))


# --- Lotes y FEFO ---


@given(re_(r"que {} también tiene (?P<n>[\d.]+) UND sin lote en {}", "sku", "alm"))
def tambien_sin_lote(ctx, sku, n, alm):
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, n, "4", alm=alm)


@when(re_(r"se solicita la salida de (?P<n>[\d.]+) UND de {} sin indicar lote", "sku"))
def salida_sin_lote(ctx, n, sku):
    ctx["textos"] = None
    mover(ctx, "SALIDA", "VENTA", sku, n)


def asignado(ctx):
    salidas = Movimiento.all_tenants.filter(pk__in=ctx.get("ids") or []).select_related("lote")
    return {(m.lote.codigo if m.lote else None): m.cantidad for m in salidas}


@then(re_(r"se asignan (?P<n>[\d.]+) UND del lote {}", "lote"))
def se_asignan(ctx, n, lote):
    assert asignado(ctx)[lote] == D(n)


@then(re_(r"se asignan (?P<n>[\d.]+) UND sin lote"))
def se_asignan_sin_lote(ctx, n):
    assert asignado(ctx)[None] == D(n)


@then(re_("no se asigna nada del lote {} porque está vencido", "lote"))
def nada_del_vencido(ctx, lote):
    assert lote not in asignado(ctx)


@then(re_(r"el lote {} queda con stock 0", "lote"))
def lote_en_cero(ctx, lote):
    assert Stock.all_tenants.get(lote__codigo=lote, empresa=ctx["empresa"]).cantidad == 0


@given(re_(r"que {} tiene vida útil de (?P<n>\d+) días", "sku"))
def vida_util(ctx, sku, n):
    producto(ctx, sku).__class__.all_tenants.filter(pk=producto(ctx, sku).pk).update(
        vida_util_dias=int(n)
    )


@when(re_(r"entra un lote {} de (?P<n>[\d.]+) UND de {} sin indicar vencimiento", "lote", "sku"))
def entra_lote(ctx, lote, n, sku):
    mover(ctx, "ENTRADA", "COMPRA", sku, n, "4", lote)


@when(
    re_(r"entra el lote {} de (?P<n>[\d.]+) UND de {} con vencimiento {}", "lote", "sku", "vence")
)
def entra_lote_con_vencimiento(ctx, lote, n, sku, vence):
    mover(ctx, "ENTRADA", "COMPRA", sku, n, "4", lote, date.fromisoformat(vence))


@then(re_("el lote {} vence el {}", "lote", "vence"))
def lote_vence(ctx, lote, vence):
    fila = Lote.all_tenants.get(empresa=ctx["empresa"], codigo=lote)
    assert fila.fecha_vencimiento == date.fromisoformat(vence)


@given(re_(r"que existe el servicio {} \(visita guiada\)", "sku"))
def existe_servicio(ctx, sku):
    crear_directo(
        ctx, sku, u="SERV", tipo="SERVICIO", se_compra=False, se_vende=True, precio_venta=30
    )


@when(re_(r"se intenta registrar una entrada de (?P<n>[\d.]+) SERV de {}", "sku"))
def entrada_de_servicio(ctx, n, sku):
    mover(ctx, "ENTRADA", "COMPRA", sku, n, "0")


# --- Almacenes (T16) ---


@given(re_("que el almacén {} tiene stock", "nombre"))
def almacen_con_stock(ctx, nombre):
    mover(ctx, "ENTRADA", "SALDO_INICIAL", ctx["sku"], "1", "4", alm=nombre)


@when(re_("intento desactivar el almacén {}", "nombre"))
def desactivar_almacen(client, ctx, nombre):
    alm = Almacen.all_tenants.get(empresa=ctx["empresa"], nombre=nombre).id
    datos = {"accion": "desactivar", "id": alm}
    respuesta = como(client, EMAIL).post("/inventario/almacenes/", datos, follow=True)
    ctx["textos"] = [contenido(respuesta)]


# --- Ajustes (0003b) ---


@given(re_(r"que {} tiene stock (?P<n>[\d.]+) (?P<u>\w+)(?: con promedio (?P<p>[\d.]+))?", "sku"))
def tiene_stock(ctx, sku, n, u, p):
    bien(ctx, sku, u)
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, n, p or "1")


@when(
    parsers.re(
        r'registro un ajuste "CONTEO"(?: de "(?P<sku>[^"]+)")?(?: del lote "(?P<lote>[^"]+)")?'
        r" con cantidad contada (?P<n>[\d.]+) (?P<u>\w+)(?: y motivo \"(?P<motivo>[^\"]+)\")?"
    )
)
def conteo(ctx, sku, lote, n, u, motivo):
    linea = LineaAjuste(producto(ctx, sku or ctx["sku"]).id, D(n), lote=lote)
    ajustar(ctx, "CONTEO", [linea], motivo or "Conteo")


def del_ajuste(ctx):
    return Movimiento.all_tenants.filter(
        empresa=ctx["empresa"], ref_tipo="AJUSTE", ref_id=ctx["ajuste"]
    ).select_related("lote")


@then(re_(r"se registra una salida de (?P<n>[\d.]+) (?P<u>\w+) a costo (?P<c>[\d.]+)"))
def salida_a_costo(ctx, n, u, c):
    [m] = del_ajuste(ctx)
    assert (m.tipo, m.cantidad, m.costo_unitario) == ("SALIDA", D(n), D(c))


@then(re_(r"se registra una salida de (?P<n>[\d.]+) (?P<u>\w+) del lote {}", "lote"))
def salida_del_lote(ctx, n, u, lote):
    [m] = del_ajuste(ctx)
    assert (m.tipo, m.cantidad, m.lote.codigo) == ("SALIDA", D(n), lote)


@then(re_(r"el stock de {} es (?P<n>[\d.]+) (?P<u>\w+)", "sku"))
def stock_es(ctx, sku, n, u):
    assert costo(ctx, sku).cantidad_total == D(n)


@then("el ajuste queda registrado con diferencia 0")
def diferencia_cero(ctx):
    linea = AjusteLinea.all_tenants.get(ajuste_id=ctx["ajuste"])
    assert linea.cantidad - linea.cantidad_sistema == 0


@then("no se genera movimiento de kardex")
def sin_movimiento(ctx):
    assert not del_ajuste(ctx).exists()


@given(re_("que existe el bien {} que se fabrica y se vende, sin movimientos", "sku"))
def bien_sin_movimientos(ctx, sku):
    crear_directo(
        ctx, sku, u="UND", se_compra=False, se_fabrica=True, se_vende=True, precio_venta=15
    )


@then(re_(r"existe el lote {} de {} con (?P<n>[\d.]+) UND en {}", "lote", "sku", "alm"))
def existe_lote(ctx, lote, sku, n, alm):
    s = Stock.all_tenants.get(
        producto=producto(ctx, sku), lote__codigo=lote, almacen_id=almacen(ctx, alm)
    )
    assert s.cantidad == D(n)


@given(re_(r'un ajuste "MERMA" de (?P<n>[\d.]+) KG de {} a costo (?P<c>[\d.]+)', "sku"))
def un_ajuste_merma(ctx, n, sku, c):
    bien(ctx, sku)
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, "100", "4")
    mover(ctx, "ENTRADA", "COMPRA", sku, "50", "5")
    ajustar(ctx, "MERMA", [LineaAjuste(producto(ctx, sku).id, D(n))], "Saco roto")
    [m] = del_ajuste(ctx)
    assert m.costo_unitario == D(c)


def anular(ctx, rol, motivo):
    email = f"{rol}@andina.pe"
    if not Usuario.objects.filter(email=email).exists():
        crear_usuario(email, ctx["empresa"], ROLES[rol])
    try:
        with tenant_context(ctx["empresa"].id):
            caso_de_ajuste(ua.AnularAjuste).ejecutar(actor(email), ctx["ajuste"], motivo)
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


@when(re_("un usuario {} lo anula con motivo {}", "rol", "motivo"))
def lo_anula(ctx, rol, motivo):
    anular(ctx, rol, motivo)


@given(re_("que un usuario {} lo anuló con motivo {}", "rol", "motivo"))
def lo_anulo(ctx, rol, motivo):
    anular(ctx, rol, motivo)


@then(re_(r'se registra una entrada "ANULACION" de (?P<n>[\d.]+) KG a costo (?P<c>[\d.]+)'))
def entrada_anulacion(ctx, n, c):
    m = del_ajuste(ctx).get(motivo="ANULACION")
    assert (m.tipo, m.cantidad, m.costo_unitario) == ("ENTRADA", D(n), D(c))


@then(re_("el ajuste queda en estado {}", "estado"))
def estado_ajuste(ctx, estado):
    assert Ajuste.all_tenants.get(pk=ctx["ajuste"]).estado == estado


@given(re_(r"{} con stock (?P<n>[\d.]+) KG en {} y costo promedio (?P<p>[\d.]+)", "sku", "alm"))
def con_stock_y_promedio(ctx, sku, n, alm, p):
    bien(ctx, sku)
    mover(ctx, "ENTRADA", "SALDO_INICIAL", sku, n, p, alm=alm)


@when(re_(r'registro un ajuste "TRANSFERENCIA" de ' + OPERACION + " de {} a {}", "o", "d"))
def transferencia(ctx, cant, u, sku, o, d):
    linea = LineaAjuste(producto(ctx, sku).id, D(cant))
    ajustar(ctx, "TRANSFERENCIA", [linea], "Reposición", alm=o, destino=d)


@then(re_(r"{} queda con (?P<a>[\d.]+) KG y {} con (?P<b>[\d.]+) KG", "o", "d"))
def quedan(ctx, o, a, d, b):
    p = producto(ctx, ctx["sku"])
    for alm, n in ((o, a), (d, b)):
        assert Stock.all_tenants.get(producto=p, almacen_id=almacen(ctx, alm)).cantidad == D(n)


@then(re_(r"la salida y la entrada se registran a costo (?P<c>[\d.]+)"))
def mismo_costo(ctx, c):
    assert sorted((m.tipo, m.costo_unitario) for m in del_ajuste(ctx)) == [
        ("ENTRADA", D(c)),
        ("SALIDA", D(c)),
    ]


@then(re_("la transferencia no aparece en {} del estado de resultados", "seccion"))
def fuera_de_resultados(ctx, seccion):
    pytest.skip("Parcial; pendiente: el estado de resultados es de 0008b")
