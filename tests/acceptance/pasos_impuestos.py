"""Pasos de los escenarios de impuestos (spec 0002e)."""

from datetime import date
from decimal import Decimal

from pytest_bdd import given, parsers, then, when

from catalog.application import impuestos as uc
from catalog.application import productos as uc_productos
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.contenedor import caso_de_impuestos, caso_de_uso, catalogo_query
from catalog.infrastructure.models import Impuesto, ImpuestoTasa, Producto, ProductoImpuesto
from purchasing.infrastructure.models import Proveedor
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from shared.domain.vigencia import valor_vigente
from tenancy.infrastructure.models import Usuario
from tests.acceptance import pasos_compras
from tests.acceptance.pasos_accesos import actor, re_
from tests.acceptance.pasos_catalogo import EMAIL, crear_directo
from tests.acceptance.pasos_sesion import crear_usuario

ADMIN = "admin.impuestos@andina.pe"
TIPO = {"venta": "VENTA", "compra": "COMPRA"}
CRITERIO = {"porcentaje": "PORCENTAJE", "monto fijo": "FIJO"}


def impuesto(ctx, nombre, tipo="venta") -> Impuesto:
    return Impuesto.all_tenants.get(empresa=ctx["empresa"], nombre=nombre, tipo=TIPO[tipo])


def admin(ctx) -> str:
    """Los "Dado" preparan datos como Administrador, con o sin el rol del escenario."""
    if not Usuario.objects.filter(email=ADMIN).exists():
        crear_usuario(ADMIN, ctx["empresa"], "Administrador")
    return ADMIN


def intentar(ctx, accion):
    """Ejecuta el caso de uso en la empresa; un rechazo queda para "la operación es rechazada"."""
    ctx["textos"] = []
    try:
        with tenant_context(ctx["empresa"].id):
            return accion()
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def definir(ctx, nombre, tipo, codigo, tasa=None, desde=None, email=EMAIL):
    def accion():
        id_ = caso_de_impuestos(uc.GuardarImpuesto).ejecutar(
            actor(email), None, nombre, TIPO[tipo.lower()], codigo
        )
        if tasa:
            agregar(id_, tasa, desde, email)

    intentar(ctx, accion)


def agregar(id_, tasa, desde, email=EMAIL):
    caso_de_impuestos(uc.AgregarTasa).ejecutar(
        actor(email), id_, Decimal(tasa), date.fromisoformat(desde)
    )


@then("la empresa tiene los impuestos:")
def tiene_impuestos(ctx, datatable):
    filas = Impuesto.all_tenants.filter(empresa=ctx["empresa"])
    esperado = {(n, TIPO[t.lower()], c) for n, t, c in datatable[1:]}
    assert set(filas.values_list("nombre", "tipo", "codigo")) == esperado


@when("defino los impuestos:")
def defino_impuestos(ctx, datatable):
    for nombre, tipo, codigo, tasa, desde in datatable[1:]:
        definir(ctx, nombre, tipo, codigo, tasa, desde)
        assert not ctx["textos"], ctx["textos"]


@when(re_("defino el impuesto {} de tipo {} con código {}", "nombre", "tipo", "codigo"))
def defino_impuesto(ctx, nombre, tipo, codigo):
    definir(ctx, nombre, tipo, codigo)


@given(re_(r"el impuesto {} de monto fijo (?P<tasa>[\d.]+) desde {}", "nombre", "desde"))
def impuesto_isc(ctx, nombre, tasa, desde):
    definir(ctx, nombre, "venta", "ISC", tasa, desde, admin(ctx))
    assert not ctx["textos"], ctx["textos"]


@when(
    parsers.re(
        r'agrego al impuesto "(?P<nombre>[^"]+)"(?: de (?P<tipo>venta|compra))? '
        r'la tasa (?P<tasa>-?[\d.]+) desde "(?P<desde>[^"]+)"'
    )
)
def agrego_tasa(ctx, nombre, tipo, tasa, desde):
    id_ = impuesto(ctx, nombre, tipo or "venta").id
    intentar(ctx, lambda: agregar(id_, tasa, desde))


@then(
    parsers.re(
        r'la tasa de "(?P<nombre>[^"]+)" es (?P<a>[\d.]+) el "(?P<fa>[^"]+)"'
        r'(?: y (?P<b>[\d.]+) el "(?P<fb>[^"]+)")?'
    )
)
def tasa_vigente(ctx, nombre, a, fa, b, fb):
    tasas = ImpuestoTasa.all_tenants.filter(impuesto=impuesto(ctx, nombre))
    historial = list(tasas.values_list("vigente_desde", "importe"))
    for valor, fecha in ((a, fa), (b, fb)):
        if valor:
            assert valor_vigente(historial, date.fromisoformat(fecha)) == Decimal(valor)


@given(re_("el bien {} con impuesto de venta {}", "sku", "nombre"))
def bien_con_impuesto(ctx, sku, nombre):
    with tenant_context(ctx["empresa"].id):
        p = crear_directo(ctx, sku, u="UND", se_vende=True, precio_venta=Decimal("12"))
        ProductoImpuesto.objects.create(producto=p, impuesto=impuesto(ctx, nombre))


@when(re_("intento desactivar el impuesto {} de (?P<tipo>venta|compra)", "nombre"))
def desactivo_impuesto(ctx, nombre, tipo):
    id_ = impuesto(ctx, nombre, tipo).id
    intentar(
        ctx, lambda: caso_de_impuestos(uc.CambiarEstadoImpuesto).ejecutar(actor(EMAIL), id_, False)
    )


# --- Impuestos del producto (UC-CAT-10) ---


def nombres(texto: str) -> list[str]:
    """ "IGV 18%" e "ISC 330 ml" · IGV 18%, Exonerado → ["IGV 18%", …]."""
    return [n.strip().strip('"') for n in texto.replace('" e "', ",").split(",") if n.strip()]


def asegurar_isc(ctx, nombre):
    """Los ejemplos usan "ISC 330 ml" sin definirlo: S/ 0.8283 desde 2024-07-01."""
    if not Impuesto.all_tenants.filter(empresa=ctx["empresa"], nombre=nombre).exists():
        definir(ctx, nombre, "venta", "ISC", "0.8283", "2024-07-01", admin(ctx))


def crear_con_impuestos(ctx, sku, tipo, lista, texto, precio="1", email=EMAIL):
    ids = []
    for n in nombres(texto):
        if n.startswith("ISC"):
            asegurar_isc(ctx, n)
        ids.append(impuesto(ctx, n, lista).id)
    servicio = tipo == "servicio"
    datos = DatosProducto(
        sku,
        sku,
        TipoProducto.SERVICIO if servicio else TipoProducto.BIEN,
        "SERV" if servicio else "UND",
        se_vende=lista == "venta" or servicio,
        se_compra=lista == "compra",
        precio_venta=Decimal(precio) if lista == "venta" or servicio else None,
    )
    listas = {f"impuestos_{lista}": ids}
    intentar(
        ctx, lambda: caso_de_uso(uc_productos.CrearProducto).ejecutar(actor(email), datos, **listas)
    )


@given(
    parsers.re(
        r'el bien "(?P<sku>[^"]+)" que se vende a (?P<precio>[\d.]+) con impuestos? de venta '
        r"(?P<texto>.+)"
    )
)
def bien_que_se_vende_con(ctx, sku, precio, texto):
    crear_con_impuestos(ctx, sku, "bien", "venta", texto, precio, admin(ctx))
    assert not ctx["textos"], ctx["textos"]


@given(
    re_(
        r"el impuesto {} de venta con criterio \"(?P<criterio>porcentaje|monto fijo)\" "
        r"y tasa (?P<tasa>[\d.]+) desde {}",
        "nombre",
        "desde",
    )
)
def impuesto_con_criterio(ctx, nombre, criterio, tasa, desde):
    def accion():
        id_ = caso_de_impuestos(uc.GuardarImpuesto).ejecutar(
            actor(EMAIL), None, nombre, "VENTA", "ISC", CRITERIO[criterio]
        )
        agregar(id_, tasa, desde)

    intentar(ctx, accion)
    assert not ctx["textos"], ctx["textos"]


@when(
    parsers.re(
        r'creo el (?P<tipo>bien|servicio) "(?P<sku>[^"]+)" con impuestos de '
        r'(?P<lista>venta|compra) "(?P<texto>[^"]+)"'
    )
)
def creo_con_impuestos(ctx, tipo, sku, lista, texto):
    crear_con_impuestos(ctx, sku, tipo, lista, texto)


def desglose(ctx, sku, total, cantidad):
    with tenant_context(ctx["empresa"].id):
        p = Producto.objects.get(sku=sku)
        return catalogo_query().desglose_de_linea(p.id, total, cantidad, date.today())


def comprobar(d, valor, isc, igv):
    assert (d.valor, d.isc, d.igv) == (Decimal(valor), Decimal(isc), Decimal(igv))


@then(
    re_(
        r"el desglose de {} es valor (?P<valor>[\d.]+), ISC (?P<isc>[\d.]+) e IGV (?P<igv>[\d.]+)",
        "sku",
    )
)
def desglose_unitario(ctx, sku, valor, isc, igv):
    with tenant_context(ctx["empresa"].id):
        precio = Producto.objects.get(sku=sku).precio_venta
    comprobar(desglose(ctx, sku, precio, Decimal("1")), valor, isc, igv)


@then(
    re_(
        r"una venta de (?P<cantidad>\d+) {} se desglosa en valor (?P<valor>[\d.]+), "
        r"ISC (?P<isc>[\d.]+) e IGV (?P<igv>[\d.]+)",
        "sku",
    )
)
def desglose_venta(ctx, cantidad, sku, valor, isc, igv):
    with tenant_context(ctx["empresa"].id):
        precio = Producto.objects.get(sku=sku).precio_venta
    q = Decimal(cantidad)
    comprobar(desglose(ctx, sku, precio * q, q), valor, isc, igv)


# --- Compras con el impuesto de compra del producto (RF-CAT-61) ---


@given(re_("el bien {} que se compra con impuesto de compra {}", "sku", "nombre"))
def bien_que_se_compra_con(ctx, sku, nombre):
    crear_con_impuestos(ctx, sku, "bien", "compra", nombre)
    assert not ctx["textos"], ctx["textos"]


@when(
    parsers.re(
        r'registro una compra con factura de (?P<n1>\d+) "(?P<s1>[^"]+)" a (?P<c1>[\d.]+) '
        r'y (?P<n2>\d+) "(?P<s2>[^"]+)" a (?P<c2>[\d.]+)'
    )
)
def compra_con_factura(ctx, n1, s1, c1, n2, s2, c2):
    Proveedor.all_tenants.get_or_create(
        empresa=ctx["empresa"],
        tipo_doc="RUC",
        num_doc="20512345671",
        defaults={"razon_social": "Maltería del Sur"},
    )
    filas = [
        {"producto": s, "cantidad": n, "costo_unitario": c}
        for s, n, c in ((s1, n1, c1), (s2, n2, c2))
    ]
    pasos_compras.crear(ctx, filas, doc="FACTURA", serie="F001-1")
    assert ctx["compra"], ctx.get("textos")


@then(
    parsers.re(r"la compra tiene subtotal (?P<s>[\d.]+), IGV (?P<i>[\d.]+) y total (?P<t>[\d.]+)")
)
def compra_tiene(ctx, s, i, t):
    c = pasos_compras.compra(ctx)
    assert (c.subtotal, c.igv, c.total) == (Decimal(s), Decimal(i), Decimal(t))
