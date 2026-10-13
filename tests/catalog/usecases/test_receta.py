"""0002a enmienda 4, T36 y T37: receta opcional en los casos de uso (RF-CAT-41, 46; RF-CAT-21)."""

from dataclasses import replace
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from catalog.application import productos as uc
from catalog.domain.errores import NoSePuedeEliminar, RecetaInvalida
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_uso, catalogo_query
from catalog.infrastructure.models import RecetaComponente

pytestmark = pytest.mark.django_db
IPA_BOTELLA = DatosProducto(
    "TER-IPA-330",
    "IPA botella",
    T.BIEN,
    "UND",
    se_vende=True,
    se_compra=False,
    se_fabrica=True,
    precio_venta=Decimal("12"),
)


def crear(actor, datos, receta=None):
    return caso_de_uso(uc.CrearProducto).ejecutar(actor, datos, receta)


def editar(actor, producto_id, datos, receta=None):
    caso_de_uso(uc.EditarProducto).ejecutar(actor, producto_id, datos, receta)


@pytest.fixture
def base(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    fabricado = {"se_compra": False, "se_fabrica": True}
    ids = {
        "granel": crear(actor, DatosProducto("GRA-IPA", "IPA a granel", T.BIEN, "L", **fabricado)),
        "botella": crear(actor, DatosProducto("ENV-BOT", "Botella", T.BIEN, "UND")),
        "caja": crear(actor, DatosProducto("ENV-CAJA", "Caja x24", T.BIEN, "UND")),
        "malta": crear(actor, DatosProducto("INS-MALTA", "Malta", T.BIEN, "KG")),
        "maquila": crear(
            actor, DatosProducto("SRV-MAQ", "Maquila", T.SERVICIO, "SERV", se_compra=True)
        ),
    }
    return actor, ids, inventario


def receta_botella(ids):
    return ((ids["granel"], Decimal("0.33")), (ids["botella"], Decimal("1")))


def test_receta_con_varios_componentes_incluido_un_servicio(base):
    actor, ids, _ = base
    ipa = crear(actor, IPA_BOTELLA, (*receta_botella(ids), (ids["maquila"], Decimal("1"))))
    assert len(catalogo_query().receta(ipa)) == 3
    assert catalogo_query().componentes_para(ipa, Decimal("1000")) == {
        ids["granel"]: Decimal("330.0000"),
        ids["botella"]: Decimal("1000.0000"),
        ids["maquila"]: Decimal("1000.0000"),
    }


def test_sin_receta_y_luego_con_un_solo_componente(base):
    actor, ids, _ = base
    granel = DatosProducto(
        "GRA-STOUT", "Stout a granel", T.BIEN, "L", se_compra=False, se_fabrica=True
    )
    stout = crear(actor, granel)
    assert catalogo_query().receta(stout) == ()
    editar(actor, stout, granel, ((ids["malta"], Decimal("0.2")),))
    assert catalogo_query().receta(stout) == ((ids["malta"], Decimal("0.2000")),)


def test_receta_solo_si_se_fabrica_y_se_conserva_al_desmarcar(base):
    actor, ids, _ = base
    agua = crear(actor, DatosProducto("MER-AGUA", "Agua", T.BIEN, "UND"), receta_botella(ids))
    assert catalogo_query().receta(agua) == ()  # no se fabrica: se ignora
    ipa = crear(actor, IPA_BOTELLA, receta_botella(ids))
    editar(actor, ipa, replace(IPA_BOTELLA, se_fabrica=False, se_compra=True), ())
    assert len(catalogo_query().receta(ipa)) == 2  # oculta, no borrada


def test_rechazos_de_la_receta(base):
    actor, ids, _ = base
    ipa = crear(actor, IPA_BOTELLA, receta_botella(ids))
    with pytest.raises(RecetaInvalida, match="componente de sí mismo"):
        editar(actor, ipa, IPA_BOTELLA, ((ipa, Decimal("1")),))
    granel = DatosProducto("GRA-IPA", "IPA a granel", T.BIEN, "L", se_compra=False)
    with pytest.raises(RecetaInvalida, match="crea un ciclo"):
        editar(actor, ids["granel"], replace(granel, se_fabrica=True), ((ipa, Decimal("1")),))
    caso_de_uso(uc.CambiarEstadoProducto).ejecutar(actor, ids["caja"], False)
    with pytest.raises(RecetaInvalida, match="no existe o está inactivo"):
        editar(actor, ipa, IPA_BOTELLA, ((ids["caja"], Decimal("1")),))


def test_componente_usado_no_se_elimina_pero_se_desactiva(base):
    actor, ids, _ = base
    crear(actor, IPA_BOTELLA, receta_botella(ids))
    with pytest.raises(NoSePuedeEliminar):
        caso_de_uso(uc.EliminarProducto).ejecutar(actor, ids["botella"])
    caso_de_uso(uc.CambiarEstadoProducto).ejecutar(actor, ids["granel"], False)


def test_con_movimientos_la_receta_y_los_litros_se_editan(base):
    """Los litros por unidad son informativos (0002e, RF-CAT-58): ya no se bloquean."""
    actor, ids, inventario = base
    datos = replace(IPA_BOTELLA, contenido_litros=Decimal("0.33"))
    ipa = crear(actor, datos, receta_botella(ids))
    inventario.con_movimientos.add(ipa)
    editar(actor, ipa, replace(datos, contenido_litros=Decimal("0.5")))
    editar(actor, ipa, replace(datos, nombre="IPA botella 330"), ((ids["botella"], Decimal(1)),))
    assert catalogo_query().receta(ipa) == ((ids["botella"], Decimal("1.0000")),)


def test_constraints_de_la_receta(base):
    actor, ids, _ = base
    ipa = crear(actor, IPA_BOTELLA, receta_botella(ids))
    for kw in (
        {"componente_id": ids["botella"], "cantidad_por_unidad": 2},
        {"componente_id": ids["caja"], "cantidad_por_unidad": 0},
        {"componente_id": ipa, "cantidad_por_unidad": 1},
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            RecetaComponente.objects.create(producto_id=ipa, **kw)
