"""Pasos de los escenarios de órdenes de producción (spec 0005a)."""

from datetime import timedelta
from decimal import Decimal as D

from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from catalog.infrastructure.models import RecetaComponente
from inventory.infrastructure.models import Movimiento, Stock
from production.application import ordenes as uc
from production.infrastructure.contenedor import caso_de_op
from production.infrastructure.models import OpComponente, OrdenProduccion
from production.interfaces.views import _componentes
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import Rol, RolPermiso, Usuario, UsuarioRol
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_catalogo import EMAIL, ROLES, crear_directo, producto
from tests.acceptance.pasos_inventario import almacen, mover
from tests.acceptance.pasos_sesion import crear_usuario


def email(ctx) -> str:
    return ctx.get("email", EMAIL)


def intentar(ctx, accion):
    """Ejecuta en la empresa; un rechazo queda para "la operación es rechazada"."""
    ctx["textos"] = []
    try:
        with tenant_context(ctx["empresa"].id):
            return accion()
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def op(ctx) -> OrdenProduccion:
    return OrdenProduccion.all_tenants.get(pk=ctx["op"])


def stock(ctx, sku, lote=None) -> D:
    filas = Stock.all_tenants.filter(empresa=ctx["empresa"], producto=producto(ctx, sku))
    if lote:
        filas = filas.filter(lote__codigo=lote)
    return sum((s.cantidad for s in filas), D("0"))


# --- Antecedentes ---


@given(
    parsers.re(
        r'el bien que se fabrica "(?P<sku>[^"]+)" en "(?P<u>[^"]+)"'
        r"(?: con vida útil (?P<dias>\d+) días y| con) receta por unidad:"
    )
)
def fabricado_con_receta(ctx, sku, u, dias, datatable):
    p = crear_directo(
        ctx,
        sku,
        u=u,
        se_compra=False,
        se_fabrica=True,
        vida_util_dias=int(dias) if dias else None,
    )
    for componente, cantidad in datatable[1:]:
        RecetaComponente.objects.create(
            producto=p, componente=crear_directo(ctx, componente), cantidad_por_unidad=D(cantidad)
        )


@given(re_(r"el stock en {} con costo promedio:", "alm"))
def stock_con_costo(ctx, alm, datatable):
    for sku, cantidad, costo in datatable[1:]:
        crear_directo(ctx, sku)
        mover(ctx, "ENTRADA", "COMPRA", sku, cantidad, costo, alm=alm)


@given("los bienes que se compran con stock y costo:")
def comprados_con_stock(ctx, datatable):
    for sku, cantidad, costo in datatable[1:]:
        crear_directo(ctx, sku, u="UND")
        mover(ctx, "ENTRADA", "COMPRA", sku, cantidad, costo)


@given(re_(r"el lote {} de {} con (?P<n>[\d.]+) L a costo (?P<c>[\d.]+)", "lote", "sku"))
def lote_con_stock(ctx, lote, sku, n, c):
    mover(ctx, "ENTRADA", "COMPRA", sku, n, c, lote)


@given(re_("que trabajo como usuario {}", "rol"))
def trabajo_como(ctx, rol):
    ctx["email"] = f"{rol}@andina.pe"
    crear_usuario(ctx["email"], ctx["empresa"], ROLES[rol])


@given(re_("que a mi rol se le quita el permiso {}", "permiso"))
def sin_permiso(ctx, permiso):
    usuario = Usuario.objects.get(email=email(ctx))
    roles = Rol.all_tenants.filter(pk__in=UsuarioRol.objects.filter(usuario=usuario).values("rol"))
    RolPermiso.objects.filter(rol__in=roles, permiso_id=permiso).delete()


# --- Crear y preparar la OP ---


def crear(ctx, n, sku, comentario=""):
    datos = uc.DatosOp(
        producto(ctx, sku).id,
        D(n),
        timezone.localdate(),
        almacen(ctx),
        almacen(ctx),
        comentario=comentario,
    )
    ctx["receta"] = list(
        RecetaComponente.objects.filter(producto__sku=sku).values_list(
            "componente_id", "cantidad_por_unidad"
        )
    )
    ctx["op"] = intentar(ctx, lambda: caso_de_op(uc.CrearOp).ejecutar(actor(email(ctx)), datos))
    return ctx["op"]


def en_proceso(ctx):
    intentar(ctx, lambda: caso_de_op(uc.PasarAEnProceso).ejecutar(actor(EMAIL), ctx["op"]))


def finalizar(ctx, producida, consumos=(), indirecto="0", motivo=""):
    reales = tuple(uc.ConsumoReal(producto(ctx, s).id, D(q)) for s, q in consumos)
    f = uc.Finalizacion(D(producida), timezone.localdate(), reales, D(indirecto), "", None, motivo)
    hoy = timezone.localdate()
    ctx["avisos"] = intentar(
        ctx, lambda: caso_de_op(uc.FinalizarOp).ejecutar(actor(email(ctx)), ctx["op"], f, hoy)
    )


@when(re_(r"creo una OP de (?P<n>[\d.]+) {} con su receta y el comentario {}", "sku", "texto"))
def creo_op(ctx, n, sku, texto):
    crear(ctx, n, sku, texto)


@given(
    parsers.re(
        r'una OP de (?P<n>[\d.]+) "(?P<sku>[^"]+)" (?P<estado>creada|en proceso) con su receta'
    )
)
def una_op(ctx, n, sku, estado):
    crear(ctx, n, sku)
    if estado == "en proceso":
        en_proceso(ctx)


@given(parsers.re(r'una OP de (?P<n>[\d.]+) "(?P<sku>[^"]+)" en estado "(?P<estado>[^"]+)"'))
def op_en_estado(ctx, n, sku, estado):
    crear(ctx, n, sku)
    if estado == "Finalizada":
        en_proceso(ctx)
        finalizar(ctx, "425")
    elif estado == "Anulada":
        anular = caso_de_op(uc.AnularOp)
        intentar(ctx, lambda: anular.ejecutar(actor(email(ctx)), ctx["op"], "x"))


@given(
    parsers.re(r'una OP de (?P<n>[\d.]+) "(?P<sku>[^"]+)" finalizada con (?P<p>[\d.]+) producidos')
)
def op_finalizada(ctx, n, sku, p):
    crear(ctx, n, sku)
    en_proceso(ctx)
    finalizar(ctx, p)


@when(
    parsers.re(
        r'cambio en la OP "(?P<a>[^"]+)" a (?P<qa>[\d.]+) y agrego "(?P<b>[^"]+)" (?P<qb>[\d.]+)'
    )
)
def cambio_componentes(ctx, a, qa, b, qb):
    from production.domain.op import Componente

    crear_directo(ctx, b)
    fila = op(ctx)
    with tenant_context(ctx["empresa"].id):
        actuales = list(fila.componentes.select_related("producto").order_by("id"))
    lista = [
        Componente(c.producto_id, D(qa) if c.producto.sku == a else c.por_consumir)
        for c in actuales
    ] + [Componente(producto(ctx, b).id, D(qb))]
    datos = uc.DatosOp(
        fila.producto_id,
        fila.cantidad,
        fila.fecha_programada,
        fila.almacen_origen_id,
        fila.almacen_destino_id,
        fila.responsable_id,
        fila.comentario,
        tuple(lista),
    )
    intentar(ctx, lambda: caso_de_op(uc.EditarOp).ejecutar(actor(email(ctx)), fila.id, datos))
    assert not ctx["textos"], ctx["textos"]


# --- Finalizar y anular ---


@when(
    parsers.re(
        r'la finalizo con (?P<q>[\d.]+) de "(?P<sku>[^"]+)"(?:,| y) (?P<n>[\d.]+) producidos'
        r"(?: y costo indirecto (?P<ind>[\d.]+))?"
    )
)
def finalizo_con_consumo(ctx, q, sku, n, ind):
    finalizar(ctx, n, [(sku, q)], ind or "0")


@when(parsers.re(r'la finalizo con (?P<n>[\d.]+) producidos(?: y el motivo "(?P<motivo>[^"]*)")?'))
def finalizo(ctx, n, motivo):
    finalizar(ctx, n, motivo=motivo or "")


@when(re_(r"dos usuarios la finalizan a la vez con (?P<n>[\d.]+) producidos"))
def dos_finalizan(ctx, n):
    """La concurrencia real se prueba con dos hilos en `test_concurrencia.py` (RF-PRD-12);
    aquí, la segunda finalización encuentra la OP ya finalizada."""
    finalizar(ctx, n)
    finalizar(ctx, n)
    ctx["segunda"] = ctx["textos"]


@when(re_("anulo la OP con el motivo {}", "motivo"))
def anulo(ctx, motivo):
    intentar(ctx, lambda: caso_de_op(uc.AnularOp).ejecutar(actor(email(ctx)), ctx["op"], motivo))


@when(parsers.re(r"intento (?P<accion>anular|finalizar|editar) la OP"))
def intento(ctx, accion):
    a, fila = actor(email(ctx)), op(ctx)
    datos = uc.DatosOp(
        fila.producto_id,
        fila.cantidad,
        fila.fecha_programada,
        fila.almacen_origen_id,
        fila.almacen_destino_id,
    )
    hoy = timezone.localdate()
    acciones = {
        "anular": lambda: caso_de_op(uc.AnularOp).ejecutar(a, fila.id, "x"),
        "finalizar": lambda: caso_de_op(uc.FinalizarOp).ejecutar(
            a, fila.id, uc.Finalizacion(D("1"), hoy), hoy
        ),
        "editar": lambda: caso_de_op(uc.EditarOp).ejecutar(a, fila.id, datos),
    }
    intentar(ctx, acciones[accion])


@when("abro la OP")
def abro_op(client, ctx):
    ctx["pagina"] = contenido(como(client, email(ctx)).get(f"/produccion/{ctx['op']}/"))


# --- Resultados ---


@then(re_(r"la OP {} queda {} sin movimientos de stock", "numero", "estado"))
def op_creada(ctx, numero, estado):
    fila = op(ctx)
    assert (f"OP-{fila.numero:06d}", fila.estado) == (numero, {"Creada": "CREADA"}[estado])
    assert not Movimiento.all_tenants.filter(ref_tipo="OP", ref_id=fila.id).exists()


@then("sus componentes son:")
def componentes_son(ctx, datatable):
    with tenant_context(ctx["empresa"].id):
        filas = _componentes(op(ctx), timezone.localdate(), True)
    vistos = [
        (
            x["c"].producto.sku,
            f"{x['c'].por_consumir:.4f}",
            "Disponible" if x["disponible"] else "No disponible",
        )
        for x in filas
    ]
    assert vistos == [tuple(f) for f in datatable[1:]]


@then(re_("{} aparece {} en la OP", "sku", "estado"))
def aparece(ctx, sku, estado):
    with tenant_context(ctx["empresa"].id):
        filas = _componentes(op(ctx), timezone.localdate(), True)
    x = next(x for x in filas if x["c"].producto.sku == sku)
    assert ("Disponible" if x["disponible"] else "No disponible") == estado


@then(re_("la receta de {} no cambia", "sku"))
def receta_no_cambia(ctx, sku):
    actual = RecetaComponente.objects.filter(producto__sku=sku).values_list(
        "componente_id", "cantidad_por_unidad"
    )
    assert list(actual) == ctx["receta"]


@then(
    parsers.re(
        r'la OP queda "(?P<estado>[^"]+)"(?: con la advertencia "(?P<aviso>[^"]+)")?'
        r'(?: sin lote de "(?P<sku>[^"]+)")?'
    )
)
def op_queda(ctx, estado, aviso, sku):
    assert not ctx.get("textos"), ctx.get("textos")
    estados = {"Finalizada": "FINALIZADA", "Anulada": "ANULADA", "En proceso": "EN_PROCESO"}
    fila = op(ctx)
    assert fila.estado == estados[estado]
    if aviso:
        assert ctx["avisos"] == [aviso]
    if sku:
        assert fila.lote_codigo == "" and stock(ctx, sku) == 0


@then(re_(r"el stock de {} es (?P<n>[\d.]+)", "sku"))
def stock_es(ctx, sku, n):
    assert stock(ctx, sku) == D(n)


@then(
    parsers.re(
        r'el lote "(?P<lote>[^"]+)" de "(?P<sku>[^"]+)" tiene (?P<n>[\d.]+) a costo (?P<c>[\d.]+)'
        r"(?: y vence (?P<dias>\d+) días después)?"
    )
)
def lote_tiene(ctx, lote, sku, n, c, dias):
    assert stock(ctx, sku, lote) == D(n)
    entrada = Movimiento.all_tenants.get(
        ref_tipo="OP", ref_id=ctx["op"], tipo="ENTRADA", producto=producto(ctx, sku)
    )
    assert (entrada.lote.codigo, entrada.costo_unitario) == (lote, D(c))
    if dias:
        assert entrada.lote.fecha_vencimiento == timezone.localdate() + timedelta(days=int(dias))


@then(re_(r"la merma de {} en la OP es (?P<n>-?[\d.]+)", "sku"))
def merma(ctx, sku, n):
    c = OpComponente.all_tenants.get(op_id=ctx["op"], producto=producto(ctx, sku))
    assert c.consumido - c.por_consumir == D(n)


@then(re_("se sugiere el lote {}", "lote"))
def lote_sugerido(ctx, lote):
    assert op(ctx).lote_codigo == lote  # se finalizó sin indicar lote: quedó el sugerido


@then(re_(r"el lote {} de {} queda con (?P<n>[\d.]+)", "lote", "sku"))
def lote_queda(ctx, lote, sku, n):
    assert stock(ctx, sku, lote) == D(n)


@then("no se registró ningún movimiento de stock")
def sin_movimientos(ctx):
    assert not Movimiento.all_tenants.filter(ref_tipo="OP", ref_id=ctx["op"]).exists()


@then(re_(r"la OP registra una pérdida de producción de (?P<n>[\d.]+)"))
def perdida(ctx, n):
    assert op(ctx).perdida == D(n)


@then("la OP se finaliza una sola vez")
def una_sola_vez(ctx):
    assert ctx["segunda"] == ["La OP está finalizada"]
    entradas = Movimiento.all_tenants.filter(ref_tipo="OP", ref_id=ctx["op"], tipo="ENTRADA")
    assert entradas.count() == 1


@then(re_("no veo importes en su pestaña {}", "pestana"))
def sin_importes(ctx, pestana):
    seccion = ctx["pagina"].split(f"<h2>{pestana}</h2>")[1].split("</section>")[0]
    assert "Tu rol no puede ver costos" in seccion and "S/" not in seccion
