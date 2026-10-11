"""0002a enmienda 4, T38 y T39: ISC en la ficha del producto (RF-CAT-45, 46; RF-CAT-23 a 27)."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction

from catalog.application import productos as uc
from catalog.domain.errores import ContenidoInmutable, IscInvalido, IscSinTarifaVigente
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_uso, catalogo_query
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado

pytestmark = pytest.mark.django_db
IPA = DatosProducto(
    "TER-IPA-330",
    "IPA botella",
    T.BIEN,
    "UND",
    se_vende=True,
    se_compra=False,
    se_fabrica=True,
    precio_venta=Decimal("12"),
    isc_sistema="ESPECIFICO",
    isc_codigo_tipo_sistema="02",
    contenido_litros=Decimal("0.33"),
)
JULIO_2024 = (Decimal("2.51"), date(2024, 7, 1))


@pytest.fixture
def ipa(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    return actor, caso_de_uso(uc.CrearProducto).ejecutar(actor, IPA, None, JULIO_2024)


def test_afecto_requiere_su_primera_tasa(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    with pytest.raises(IscInvalido, match="Registra la tasa de ISC"):
        caso_de_uso(uc.CrearProducto).ejecutar(actor, IPA)


def test_tasa_nueva_con_vigencia_y_la_aplicable_a_la_fecha(ipa):
    actor, producto = ipa
    caso_de_uso(uc.AgregarTasaIsc).ejecutar(actor, producto, Decimal("2.70"), date(2027, 1, 1))
    q = catalogo_query()
    assert q.isc_aplicable(producto, date(2026, 12, 31)).monto_por_litro == Decimal("2.51")
    dto = q.isc_aplicable(producto, date(2027, 1, 1))
    assert (dto.monto_por_litro, dto.codigo_tributo, dto.codigo_tipo_sistema) == (
        Decimal("2.70"),
        "2000",
        "02",
    )
    assert q.isc_de_linea(producto, Decimal("24"), date(2026, 12, 31)) == Decimal("19.88")
    assert q.isc_de_linea(producto, Decimal("24"), date(2027, 1, 1)) == Decimal("21.38")
    with pytest.raises(IscSinTarifaVigente):
        q.isc_aplicable(producto, date(2024, 6, 30))
    with pytest.raises(IscInvalido, match="Ya hay una tasa de ISC vigente desde 2027-01-01"):
        caso_de_uso(uc.AgregarTasaIsc).ejecutar(actor, producto, Decimal("3"), date(2027, 1, 1))


def test_contenido_sugerido_desde_la_receta_33_centilitros():
    from catalog.domain.isc import contenido_sugerido

    receta = [(1, Decimal("0.33")), (2, Decimal("1"))]
    assert contenido_sugerido(receta, {1: "L", 2: "UND"}) == Decimal("0.3300")


def test_tasas_inmutables_en_la_base(ipa):
    for sql in (
        "UPDATE catalog_productoisctasa SET monto_por_litro=9",
        "DELETE FROM catalog_productoisctasa",
    ):
        with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as c:
            c.execute(sql)


def test_no_afecto_no_paga_y_desmarcar_conserva_las_tasas(ipa):
    actor, producto = ipa
    sin_isc = replace(IPA, isc_sistema=None)
    caso_de_uso(uc.EditarProducto).ejecutar(actor, producto, sin_isc)
    assert catalogo_query().isc_de_linea(producto, Decimal("10"), date.today()) == Decimal("0.00")
    caso_de_uso(uc.EditarProducto).ejecutar(actor, producto, IPA)  # vuelve: tasas conservadas
    assert catalogo_query().isc_aplicable(producto, date.today()).monto_por_litro == Decimal("2.51")


def test_contenido_bloqueado_con_movimientos(ipa, inventario):
    actor, producto = ipa
    inventario.con_movimientos.add(producto)
    with pytest.raises(ContenidoInmutable):
        caso_de_uso(uc.EditarProducto).ejecutar(
            actor, producto, replace(IPA, contenido_litros=Decimal("0.5"))
        )


def test_el_isc_lo_gestiona_quien_tiene_su_permiso(ipa):
    actor, producto = ipa
    sin_isc = Actor(actor.usuario_id, actor.empresa_id, actor.permisos - {uc.ISC})
    with pytest.raises(AccesoDenegado):
        caso_de_uso(uc.EditarProducto).ejecutar(sin_isc, producto, replace(IPA, isc_sistema=None))
    with pytest.raises(AccesoDenegado):
        caso_de_uso(uc.AgregarTasaIsc).ejecutar(sin_isc, producto, Decimal("3"), date(2028, 1, 1))
    caso_de_uso(uc.EditarProducto).ejecutar(sin_isc, producto, replace(IPA, nombre="IPA 330"))
