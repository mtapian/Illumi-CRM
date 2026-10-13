"""Pasos de los escenarios de facturación, entrega y cobranza (spec 0006b)."""

import threading
import types
import uuid
from datetime import date
from decimal import Decimal as D

from django.db import connection
from pytest_bdd import given, parsers, then, when

from catalog.infrastructure.models import Impuesto, Producto, ProductoImpuesto
from inventory.infrastructure.models import Movimiento
from sales.application import cobranzas as ucob
from sales.application import facturacion as uf
from sales.domain.facturacion import CONTADO, CREDITO, Cuota
from sales.domain.pedido import numero_pedido
from sales.infrastructure.contenedor import (
    caso_de_cobranza,
    caso_de_factura,
    caso_de_venta_directa,
    metodos_activos,
    sembrar_metodos_pago,
)
from sales.infrastructure.models import Cliente, Cobranza, MetodoPago, Pago, Pedido
from sales.interfaces import cobranzas as pantallas_cobranzas
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import Usuario
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_catalogo import EMAIL, crear_directo, producto
from tests.acceptance.pasos_inventario import almacen, mover
from tests.acceptance.pasos_sesion import crear_usuario
from tests.acceptance.pasos_ventas import (
    ESTADOS,
    aprobar,
    crear_pedido,
    hoy,
    intentar,
    pedido,
)

ESTADOS |= {"Facturado": "FACTURADO", "Entregado": "ENTREGADO"}
COBRO = {"Pendiente": "PENDIENTE", "Parcial": "PARCIAL", "Pagada": "PAGADA"}
COMPROBANTE = {"Factura": "FACTURA", "Boleta": "BOLETA"}


def como_rol(ctx, rol) -> str:
    """El correo de un usuario de la empresa con ese rol (lo crea si falta)."""
    if rol == "ventas":
        return EMAIL
    correo = f"{rol}@andina.pe"
    if not Usuario.objects.filter(email=correo).exists():
        crear_usuario(correo, ctx["empresa"], rol.capitalize())
    return correo


def cobranza(ctx) -> Cobranza:
    return Cobranza.all_tenants.get(pedido_id=ctx["pedido"])


def facturar(ctx, forma=CONTADO, cuotas=(), lotes=None, alm="Principal", pedido_id=None):
    datos = uf.DatosFactura(almacen(ctx, alm), forma, tuple(cuotas), lotes or {})
    caso = caso_de_factura(uf.FacturarPedido)
    id_ = pedido_id or ctx["pedido"]
    intentar(ctx, lambda: caso.ejecutar(actor(EMAIL), id_, datos, hoy(ctx)))
    if not ctx["textos"]:  # "el resultado es <Factura|Boleta|facturado>"
        tipo = Pedido.all_tenants.get(pk=id_).comprobante
        ctx["textos"] = [f"{tipo.title()} facturado"]


def cuotas_de(datatable) -> list[Cuota]:
    return [Cuota(D(m), date.fromisoformat(v)) for m, v in datatable[1:]]


# --- Antecedentes ---


@given(
    re_(
        r"{} se vende a (?P<precio>[\d.]+) con {}, costo promedio (?P<costo>[\d.]+) "
        r"y stock en {}:",
        "sku",
        "impuesto",
        "alm",
    )
)
def se_vende_con_stock(ctx, sku, precio, impuesto, costo, alm, datatable):
    """Bien que se vende con su impuesto de venta (0002e) y stock por lote; la empresa tiene
    sus métodos de pago (sembrador de 0001a, RF-VEN-58)."""
    p = crear_directo(
        ctx, sku, u="UND", se_compra=False, se_vende=True, se_fabrica=True, precio_venta=D(precio)
    )
    igv = Impuesto.all_tenants.get(empresa=ctx["empresa"], nombre=impuesto, tipo="VENTA")
    ProductoImpuesto.all_tenants.create(empresa=ctx["empresa"], producto=p, impuesto=igv)
    for lote, vence, cantidad in datatable[1:]:
        mover(ctx, "ENTRADA", "COMPRA", sku, cantidad, costo, lote, date.fromisoformat(vence), alm)
    sembrar_metodos_pago(ctx["empresa"].id, None, hoy(ctx))


@given(re_("el cliente {} con DNI {}", "nombre", "dni"))
def cliente_con_dni(ctx, nombre, dni):
    Cliente.all_tenants.create(empresa=ctx["empresa"], nombre=nombre, tipo_doc="DNI", num_doc=dni)


# --- Facturar y entregar ---


@when(re_("facturo el pedido desde {} al contado", "alm"))
def facturo_contado(ctx, alm):
    facturar(ctx, alm=alm)


@when(re_("facturo el pedido eligiendo el lote {}", "lote"))
def facturo_con_lote(ctx, lote):
    facturar(ctx, lotes={producto(ctx, "TER-IPA-330").id: lote})


@when("facturo el pedido a crédito con las cuotas:")
def facturo_credito(ctx, datatable):
    facturar(ctx, CREDITO, cuotas_de(datatable))


@when(re_("facturo el pedido a crédito con las cuotas {}", "cuotas"))
def facturo_credito_texto(ctx, cuotas):
    filas = []
    if cuotas != "ninguna":
        monto, vence = cuotas.split(" vence ")
        filas = [Cuota(D(monto), date.fromisoformat(vence))]
    facturar(ctx, CREDITO, filas)


@then(parsers.re(r"el pedido queda (?P<estado>Aprobado|Facturado|Entregado)"))
def pedido_queda_sin_comillas(ctx, estado):
    assert pedido(ctx).estado == ESTADOS[estado]


def salidas(pedido_id) -> dict:
    vistos = {}
    for m in Movimiento.all_tenants.filter(ref_tipo="VENTA", ref_id=pedido_id):
        vistos[m.lote.codigo] = vistos.get(m.lote.codigo, D("0")) + m.cantidad
    return vistos


@then(
    re_(
        r"salen (?P<a>\d+) unidades del lote {} y (?P<b>\d+) del lote {} "
        r"con costo total (?P<costo>[\d.]+)",
        "l1",
        "l2",
    )
)
def salen_dos_lotes(ctx, a, l1, b, l2, costo):
    assert salidas(ctx["pedido"]) == {l1: D(a), l2: D(b)}
    assert pedido(ctx).costo_total == D(costo)


@then(re_(r"salen (?P<n>\d+) unidades del lote {}", "lote"))
def salen_de_un_lote(ctx, n, lote):
    assert salidas(ctx["pedido"]) == {lote: D(n)}


@then(
    re_(
        r"el comprobante pendiente es una {} del {} con una línea de (?P<n>\d+) unidades:",
        "tipo",
        "fecha",
    )
)
def comprobante_pendiente(ctx, tipo, fecha, n, datatable):
    with tenant_context(ctx["empresa"].id):
        _comprobante(ctx, tipo, fecha, n, datatable)


def _comprobante(ctx, tipo, fecha, n, datatable):
    p = pedido(ctx)
    assert (p.comprobante, p.fecha_emision) == (COMPROBANTE[tipo], date.fromisoformat(fecha))
    (x,) = p.lineas.all()
    ((valor, isc, igv, total),) = datatable[1:]
    assert (x.cantidad, x.valor, x.isc, x.igv, x.subtotal) == (
        D(n), D(valor), D(isc), D(igv), D(total)
    )  # fmt: skip


@then(re_(r"la cobranza queda Pendiente por (?P<total>[\d.]+) con vencimiento {}", "fecha"))
def cobranza_contado(ctx, total, fecha):
    with tenant_context(ctx["empresa"].id):
        c = cobranza(ctx)
        vencimientos = [q.vencimiento for q in c.cuotas.all()]
    assert (c.estado, c.total) == ("PENDIENTE", D(total))
    assert vencimientos == [date.fromisoformat(fecha)]


@then(re_(r"la cobranza queda Pendiente por (?P<total>[\d.]+) con próximo vencimiento {}", "f"))
def cobranza_credito(ctx, total, f):
    with tenant_context(ctx["empresa"].id):
        c = pantallas_cobranzas._preparar(cobranza(ctx), hoy(ctx))
    assert (c.estado, c.total, c.proximo) == ("PENDIENTE", D(total), date.fromisoformat(f))


@then("no hay cobranzas")
def no_hay_cobranzas(ctx):
    assert not Cobranza.all_tenants.filter(empresa=ctx["empresa"]).exists()


@given(re_(r"una salida de (?P<n>\d+) {} del lote {}", "sku", "lote"))
def una_salida(ctx, n, sku, lote):
    mover(ctx, "SALIDA", "MERMA", sku, n, lote=lote)


@given(re_("el producto {} está inactivo", "sku"))
def producto_inactivo(ctx, sku):
    Producto.all_tenants.filter(pk=producto(ctx, sku).id).update(activo=False)


@then(
    re_(
        r"la factura declara forma de pago {} con monto pendiente (?P<m>[\d.]+) "
        r"y (?P<n>\d+) cuotas",
        "forma",
    )
)
def declara_credito(ctx, forma, m, n):
    p, c = pedido(ctx), cobranza(ctx)
    assert (p.comprobante, p.forma_pago) == ("FACTURA", {"Crédito": CREDITO}[forma])
    with tenant_context(ctx["empresa"].id):
        assert (c.total, c.cuotas.count()) == (D(m), int(n))


@given(re_(r"dos pedidos aprobados de {} con (?P<n>\d+) {} cada uno", "nombre", "sku"))
def dos_pedidos(ctx, nombre, n, sku):
    ctx["pedidos"] = []
    for _ in range(2):
        crear_pedido(ctx, nombre, [(sku, n)])
        aprobar(ctx)
        assert not ctx["textos"], ctx["textos"]
        ctx["pedidos"].append(ctx["pedido"])


@when("dos usuarios facturan los dos pedidos al mismo tiempo")
def facturan_a_la_vez(ctx):
    """Con transacciones reales (ver test_e06b.py): cada hilo usa su propia conexión."""
    barrera, ctx["resultados"] = threading.Barrier(2), []
    datos = uf.DatosFactura(almacen(ctx))
    caso, quien = caso_de_factura(uf.FacturarPedido), actor(EMAIL)

    def facturar_en_hilo(pedido_id):
        try:
            with tenant_context(ctx["empresa"].id):
                barrera.wait(timeout=5)
                caso.ejecutar(quien, pedido_id, datos, hoy(ctx))
            ctx["resultados"].append("ok")
        except DomainError as e:
            ctx["resultados"].append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=facturar_en_hilo, args=(p,)) for p in ctx["pedidos"]]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)


@then("solo un pedido queda Facturado")
def solo_uno(ctx):
    estados = Pedido.all_tenants.filter(pk__in=ctx["pedidos"]).values_list("estado", flat=True)
    assert sorted(estados) == ["APROBADO", "FACTURADO"] and ctx["resultados"].count("ok") == 1


@then(re_(r"el stock de {} queda en 0", "sku"))
def stock_en_cero(ctx, sku):
    with tenant_context(ctx["empresa"].id):
        from inventory.infrastructure.contenedor import inventario

        id_ = producto(ctx, sku).id
        assert inventario().disponibles([id_], hoy(ctx))[id_] == 0


@given(
    re_(
        r"un pedido facturado de {} con (?P<n>\d+) {} y costo total (?P<costo>[\d.]+)",
        "nombre",
        "sku",
    )
)
def un_pedido_facturado(ctx, nombre, n, sku, costo):
    crear_pedido(ctx, nombre, [(sku, n)])
    aprobar(ctx)
    facturar(ctx)
    assert pedido(ctx).costo_total == D(costo), ctx["textos"]


@when(re_(r"entra una compra de (?P<n>\d+) {} a costo (?P<costo>[\d.]+)", "sku"))
def entra_compra(ctx, n, sku, costo):
    mover(ctx, "ENTRADA", "COMPRA", sku, n, costo)


@then(re_(r"el costo total del pedido sigue siendo (?P<costo>[\d.]+)"))
def costo_congelado(ctx, costo):
    assert pedido(ctx).costo_total == D(costo)
    with tenant_context(ctx["empresa"].id):
        assert sum(x.costo for x in pedido(ctx).lineas.all()) == D(costo)


@when("confirmo la entrega")
def confirmo_entrega(ctx):
    caso = caso_de_factura(uf.EntregarPedido)
    intentar(ctx, lambda: caso.ejecutar(actor(EMAIL), ctx["pedido"]))
    assert not ctx["textos"], ctx["textos"]


@then("la cobranza sigue Pendiente")
def cobranza_sigue_pendiente(ctx):
    assert cobranza(ctx).estado == "PENDIENTE"


# --- Venta directa ---


@when(re_(r"registro una venta directa desde {} de (?P<n>\d+) {} con los pagos:", "alm", "sku"))
def venta_directa(ctx, alm, n, sku, datatable):
    with tenant_context(ctx["empresa"].id):
        metodos = {m.nombre: m.id for m in MetodoPago.objects.all()}
        generico = Cliente.objects.get(es_generico=True).id
    p = producto(ctx, sku)
    datos = uf.DatosVentaDirecta(
        generico,
        almacen(ctx, alm),
        (uf.LineaPedido(p.id, D(n), p.precio_venta),),
        tuple((metodos[m], D(monto)) for m, monto in datatable[1:]),
        uuid.uuid4(),
    )
    ctx["pedido"] = intentar(
        ctx, lambda: caso_de_venta_directa().ejecutar(actor(EMAIL), datos, hoy(ctx))
    )


@then(re_(r"el pedido de {} queda Entregado con total (?P<total>[\d.]+) y {}", "nombre", "tipo"))
def directa_entregada(ctx, nombre, total, tipo):
    p = pedido(ctx)
    assert (p.cliente.nombre, p.estado, p.total) == (nombre, "ENTREGADO", D(total))
    assert (p.comprobante, p.forma_pago) == (COMPROBANTE[tipo], CONTADO)


@then("la cobranza queda Pagada")
def cobranza_pagada(ctx):
    assert cobranza(ctx).estado == "PAGADA"


# --- Cobranzas y pagos ---


def pagar(ctx, monto, metodo):
    with tenant_context(ctx["empresa"].id):
        metodo_id = MetodoPago.objects.get(nombre=metodo).id
    datos = ucob.DatosPago(metodo_id, D(monto), hoy(ctx))
    caso, c = caso_de_cobranza(ucob.RegistrarPago), cobranza(ctx)
    intentar(ctx, lambda: caso.ejecutar(actor(EMAIL), c.id, datos, hoy(ctx)))


@given(re_(r"un pago de (?P<monto>[\d.]+) por {}", "metodo"))
def un_pago(ctx, monto, metodo):
    if D(monto):  # "un pago de 0.00": sin pagos previos
        pagar(ctx, monto, metodo)
        assert not ctx["textos"], ctx["textos"]


@when(re_(r"registro un pago de (?P<monto>[\d.]+) por {}", "metodo"))
def registro_pago(ctx, monto, metodo):
    pagar(ctx, monto, metodo)


@then(
    parsers.re(
        r"la cobranza queda (?P<estado>Pendiente|Parcial|Pagada) con saldo (?P<saldo>[\d.]+)"
    )
)
def cobranza_con_saldo(ctx, estado, saldo):
    c = cobranza(ctx)
    assert (c.estado, c.total - c.pagado) == (COBRO[estado], D(saldo))


def anular(ctx, rol, motivo, monto=None):
    vigentes = Pago.all_tenants.filter(cobranza=cobranza(ctx), anulado_en__isnull=True)
    pago = vigentes.get(monto=D(monto)) if monto else vigentes.get()
    caso, ctx["motivo"] = caso_de_cobranza(ucob.AnularPago), motivo
    intentar(ctx, lambda: caso.ejecutar(actor(como_rol(ctx, rol)), pago.id, motivo))


@when(re_(r"como usuario {} anulo el pago de (?P<monto>[\d.]+) con el motivo {}", "rol", "motivo"))
def anulo_pago_de(ctx, rol, monto, motivo):
    anular(ctx, rol, motivo, monto)
    assert not ctx["textos"], ctx["textos"]


@when(re_("como usuario {} anulo el pago con el motivo {}", "rol", "motivo"))
def anulo_pago(ctx, rol, motivo):
    anular(ctx, rol, motivo)
    assert not ctx["textos"], ctx["textos"]


@when(re_("como usuario {} intento anular el pago con el motivo {}", "rol", "motivo"))
def intento_anular(ctx, rol, motivo):
    anular(ctx, rol, motivo)


@then("el pago queda anulado con su motivo")
def pago_anulado(ctx):
    p = Pago.all_tenants.get(cobranza=cobranza(ctx), anulado_en__isnull=False)
    assert p.motivo_anulacion == ctx["motivo"]


@given(re_(r"un pedido de {} facturado a crédito el {} con las cuotas:", "nombre", "fecha"))
def facturado_a_credito_el(ctx, monkeypatch, nombre, fecha, datatable):
    """Se factura en esa fecha; luego vuelve el "hoy" del escenario. Las pantallas de
    cobranzas usan el "hoy" del escenario (fecha de negocio, art. 7.5)."""
    actual = hoy(ctx)
    ctx["hoy"] = date.fromisoformat(fecha)
    cuotas = cuotas_de(datatable)
    crear_pedido(ctx, nombre, [("TER-IPA-330", "24")], date.fromisoformat(fecha))
    aprobar(ctx)
    facturar(ctx, CREDITO, cuotas)
    assert pedido(ctx).estado == "FACTURADO", ctx["textos"]
    ctx["hoy"] = actual
    monkeypatch.setattr(
        pantallas_cobranzas, "timezone", types.SimpleNamespace(localdate=lambda: actual)
    )


@when(re_("abro las cobranzas con el filtro {}", "filtro"))
def abro_cobranzas(client, ctx, filtro):
    assert filtro == "solo vencidas"
    ctx["pagina"] = contenido(como(client, EMAIL).get("/ventas/cobranzas/", {"vencidas": "1"}))


@then(re_(r"veo la cobranza de {} marcada Vencida con monto vencido (?P<m>[\d.]+)", "nombre"))
def veo_vencida(ctx, nombre, m):
    pagina = ctx["pagina"]
    assert nombre in pagina and "Vencida" in pagina and f"S/ {m}" in pagina


@then(re_("la alerta lleva al listado de cobranzas filtrado por {}", "filtro"))
def alerta_cobranzas(ctx, filtro):
    assert filtro == "solo vencidas" and "/ventas/cobranzas/?vencidas=1" in ctx["pagina"]


@then(re_("el pedido facturado muestra {}", "texto"))
def pedido_muestra(ctx, texto):
    assert texto in ctx["indicadores"][numero_pedido(pedido(ctx).numero)]


# --- Métodos de pago ---


@then(re_("la empresa tiene los métodos de pago {}", "lista"))
def tiene_metodos(ctx, lista):
    with tenant_context(ctx["empresa"].id):
        nombres = set(MetodoPago.objects.values_list("nombre", flat=True))
    assert nombres == {n.strip() for n in lista.split(",")}


@when(re_("como usuario {} desactivo el método de pago {}", "rol", "nombre"))
def desactivo_metodo(ctx, rol, nombre):
    with tenant_context(ctx["empresa"].id):
        id_ = MetodoPago.objects.get(nombre=nombre).id
    caso = caso_de_cobranza(ucob.CambiarEstadoMetodoPago)
    intentar(ctx, lambda: caso.ejecutar(actor(como_rol(ctx, rol)), id_, False))
    assert not ctx["textos"], ctx["textos"]


@then(re_("{} no se ofrece en un pago nuevo", "nombre"))
def no_se_ofrece_metodo(ctx, nombre):
    with tenant_context(ctx["empresa"].id):
        assert nombre not in [m.nombre for m in metodos_activos()]


@when(re_("como usuario {} creo el método de pago {}", "rol", "nombre"))
def creo_metodo(ctx, rol, nombre):
    caso = caso_de_cobranza(ucob.GuardarMetodoPago)
    intentar(ctx, lambda: caso.ejecutar(actor(como_rol(ctx, rol)), None, nombre))
