"""Pasos de los escenarios de impuestos (spec 0002e)."""

from datetime import date
from decimal import Decimal

from pytest_bdd import given, parsers, then, when

from catalog.application import impuestos as uc
from catalog.infrastructure.contenedor import caso_de_impuestos
from catalog.infrastructure.models import Impuesto, ImpuestoTasa, ProductoImpuesto
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from shared.domain.vigencia import valor_vigente
from tests.acceptance.pasos_accesos import actor, re_
from tests.acceptance.pasos_catalogo import EMAIL, crear_directo

TIPO = {"venta": "VENTA", "compra": "COMPRA"}


def impuesto(ctx, nombre, tipo="venta") -> Impuesto:
    return Impuesto.all_tenants.get(empresa=ctx["empresa"], nombre=nombre, tipo=TIPO[tipo])


def intentar(ctx, accion):
    """Ejecuta el caso de uso en la empresa; un rechazo queda para "la operación es rechazada"."""
    ctx["textos"] = []
    try:
        with tenant_context(ctx["empresa"].id):
            return accion()
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


def definir(ctx, nombre, tipo, codigo, tasa=None, desde=None):
    def accion():
        id_ = caso_de_impuestos(uc.GuardarImpuesto).ejecutar(
            actor(EMAIL), None, nombre, TIPO[tipo.lower()], codigo
        )
        if tasa:
            agregar(id_, tasa, desde)

    intentar(ctx, accion)


def agregar(id_, tasa, desde):
    caso_de_impuestos(uc.AgregarTasa).ejecutar(
        actor(EMAIL), id_, Decimal(tasa), date.fromisoformat(desde)
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
    definir(ctx, nombre, "venta", "ISC", tasa, desde)
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
