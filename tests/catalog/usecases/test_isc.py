"""0002c, T3 a T7: categorías y tarifas de ISC (RF-CAT-22 a 28; RN-CAT-10)."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from catalog.application import isc as uc_isc
from catalog.application import productos as uc
from catalog.domain.errores import IscInvalido, IscSinTarifaVigente
from catalog.domain.presentacion import DatosPresentacion
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_isc, caso_de_uso, catalogo_query
from catalog.infrastructure.models import IscCategoria, IscTarifa

pytestmark = pytest.mark.django_db


@pytest.fixture
def cerveza(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    categoria = caso_de_isc(uc_isc.CrearCategoriaIsc).ejecutar(
        actor, "Cerveza", "02", Decimal("2.51"), date(2024, 7, 1)
    )
    return actor, categoria


def terminado_con_isc(actor, categoria):
    crear = caso_de_uso(uc.CrearProducto)
    granel = crear.ejecutar(actor, DatosProducto("GRA-IPA", "IPA", T.GRANEL, "L"))
    botella = crear.ejecutar(actor, DatosProducto("ENV-BOT", "Botella", T.ENVASE, "UND"))
    datos = DatosProducto(
        "TER-IPA-330",
        "IPA 330",
        T.TERMINADO,
        "UND",
        precio_venta=Decimal("12"),
        vida_util_dias=120,
        isc_categoria_id=categoria,
    )
    presentacion = DatosPresentacion(granel, Decimal("0.33"), ((botella, Decimal(1)),))
    return crear.ejecutar(actor, datos, presentacion)


def test_tarifas_inmutables_y_solo_sistema_especifico(cerveza):
    tarifa = IscTarifa.objects.get()
    with pytest.raises(DatabaseError, match="solo inserción"), transaction.atomic():
        IscTarifa.objects.filter(pk=tarifa.pk).update(monto_por_litro=3)
    with pytest.raises(DatabaseError, match="solo inserción"), transaction.atomic():
        tarifa.delete()
    with pytest.raises(IntegrityError), transaction.atomic():
        IscCategoria.objects.create(nombre="Otro", sistema="AL_VALOR", codigo_tipo_sistema="01")


def test_nueva_tarifa_con_vigencia_y_la_aplicable_a_la_fecha(cerveza):
    actor, categoria = cerveza
    ipa = terminado_con_isc(actor, categoria)
    caso_de_isc(uc_isc.AgregarTarifaIsc).ejecutar(
        actor, categoria, Decimal("2.70"), date(2027, 1, 1)
    )
    with pytest.raises(IscInvalido, match="Ya hay una tarifa vigente desde 2027-01-01"):
        caso_de_isc(uc_isc.AgregarTarifaIsc).ejecutar(
            actor, categoria, Decimal("3"), date(2027, 1, 1)
        )
    q = catalogo_query()
    assert q.isc_aplicable(ipa, date(2026, 12, 31)).monto_por_litro == Decimal("2.51")
    isc = q.isc_aplicable(ipa, date(2027, 1, 1))
    assert (
        isc.monto_por_litro,
        isc.contenido_litros,
        isc.codigo_tributo,
        isc.codigo_tipo_sistema,
    ) == (Decimal("2.70"), Decimal("0.33"), "2000", "02")
    assert q.isc_de_linea(ipa, Decimal("24"), date(2026, 12, 31)) == Decimal("19.88")
    with pytest.raises(IscSinTarifaVigente):
        q.isc_aplicable(ipa, date(2024, 6, 30))


def test_categoria_con_productos_activos_no_se_desactiva(cerveza):
    actor, categoria = cerveza
    terminado_con_isc(actor, categoria)
    estado = caso_de_isc(uc_isc.CambiarEstadoCategoriaIsc)
    with pytest.raises(IscInvalido, match="asignada a 1 productos activos"):
        estado.ejecutar(actor, categoria, False)


def test_sin_categoria_no_hay_isc(cerveza):
    actor, _ = cerveza
    ipa = terminado_con_isc(actor, None)
    assert catalogo_query().isc_aplicable(ipa, date(2026, 12, 31)) is None
    assert catalogo_query().isc_de_linea(ipa, Decimal("10"), date(2026, 12, 31)) == Decimal("0.00")
