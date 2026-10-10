"""0002b, T3 a T6: presentaciones de terminados (RF-CAT-05, 15 a 18, 20, 21)."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from catalog.application import productos as uc
from catalog.domain.errores import (
    ContenidoInmutable,
    NoSePuedeDesactivar,
    NoSePuedeEliminar,
    PresentacionInvalida,
)
from catalog.domain.presentacion import DatosPresentacion
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_uso, catalogo_query
from catalog.infrastructure.models import Presentacion, PresentacionMaterial, Producto

pytestmark = pytest.mark.django_db


def crear(actor, datos, presentacion=None):
    return caso_de_uso(uc.CrearProducto).ejecutar(actor, datos, presentacion)


@pytest.fixture
def base(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    ids = {
        "granel": crear(actor, DatosProducto("GRA-IPA", "IPA a granel", T.GRANEL, "L")),
        "botella": crear(actor, DatosProducto("ENV-BOT", "Botella", T.ENVASE, "UND")),
        "caja": crear(actor, DatosProducto("ENV-CAJA", "Caja x24", T.ENVASE, "UND")),
        "precinto": crear(actor, DatosProducto("ENV-PREC", "Precinto", T.ENVASE, "UND")),
        "malta": crear(actor, DatosProducto("INS-MALTA", "Malta", T.INSUMO, "KG")),
    }
    return actor, ids, inventario


def terminado(sku, nombre="IPA botella", vida=120):
    return DatosProducto(
        sku, nombre, T.TERMINADO, "UND", precio_venta=Decimal("12"), vida_util_dias=vida
    )


def botella_330(ids, contenido="0.33"):
    materiales = ((ids["botella"], Decimal("1")), (ids["caja"], Decimal("0.0417")))
    return DatosPresentacion(ids["granel"], Decimal(contenido), materiales)


def test_crear_terminado_con_presentacion_y_varias_por_granel(base):
    actor, ids, _ = base
    ipa = crear(actor, terminado("TER-IPA-330"), botella_330(ids))
    barril = DatosPresentacion(ids["granel"], Decimal("20"), ((ids["precinto"], Decimal("1")),))
    crear(actor, terminado("TER-IPA-B20", "IPA barril"), barril)
    assert Presentacion.objects.filter(granel_id=ids["granel"]).count() == 2
    assert Producto.objects.get(pk=ipa).controla_lote
    assert catalogo_query().materiales_para(ipa, Decimal("240")) == {
        ids["botella"]: Decimal("240.0000"),
        ids["caja"]: Decimal("10.0080"),
    }


def test_un_terminado_invalido_no_deja_nada(base):
    actor, ids, _ = base
    with pytest.raises(PresentacionInvalida, match="requiere al menos un material"):
        crear(actor, terminado("TER-X"), DatosPresentacion(ids["granel"], Decimal("0.33"), ()))
    with pytest.raises(PresentacionInvalida, match="tipo ENVASE"):
        crear(
            actor,
            terminado("TER-X"),
            DatosPresentacion(ids["granel"], Decimal("0.33"), ((ids["malta"], Decimal(1)),)),
        )
    with pytest.raises(PresentacionInvalida, match="Un terminado requiere su presentación"):
        crear(actor, terminado("TER-X"))
    assert not Producto.objects.filter(sku="TER-X").exists()


def test_contenido_bloqueado_con_movimientos_y_materiales_para_envasados_futuros(base):
    actor, ids, inventario = base
    ipa = crear(actor, terminado("TER-IPA-330"), botella_330(ids))
    inventario.con_movimientos.add(ipa)
    editar = caso_de_uso(uc.EditarProducto)
    with pytest.raises(ContenidoInmutable):
        editar.ejecutar(actor, ipa, terminado("TER-IPA-330"), botella_330(ids, "0.5"))
    solo_botella = DatosPresentacion(
        ids["granel"], Decimal("0.33"), ((ids["botella"], Decimal(1)),)
    )
    editar.ejecutar(actor, ipa, terminado("TER-IPA-330"), solo_botella)
    assert catalogo_query().materiales_para(ipa, Decimal("1")) == {
        ids["botella"]: Decimal("1.0000")
    }


def test_granel_con_presentaciones_no_se_desactiva_ni_se_elimina_un_material_usado(base):
    actor, ids, _ = base
    ipa = crear(actor, terminado("TER-IPA-330"), botella_330(ids))
    estado = caso_de_uso(uc.CambiarEstadoProducto)
    with pytest.raises(NoSePuedeDesactivar, match="Desactiva primero las presentaciones"):
        estado.ejecutar(actor, ids["granel"], False)
    with pytest.raises(NoSePuedeEliminar):
        caso_de_uso(uc.EliminarProducto).ejecutar(actor, ids["botella"])
    estado.ejecutar(actor, ipa, False)
    estado.ejecutar(actor, ids["granel"], False)


def test_constraints_de_presentacion(base):
    actor, ids, _ = base
    ipa = crear(actor, terminado("TER-IPA-330"), botella_330(ids))
    p = Presentacion.objects.get(producto_id=ipa)
    with pytest.raises(IntegrityError), transaction.atomic():
        PresentacionMaterial.objects.create(
            presentacion=p, material_id=ids["botella"], cantidad_por_unidad=2
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        PresentacionMaterial.objects.create(
            presentacion=p, material_id=ids["precinto"], cantidad_por_unidad=0
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Presentacion.objects.filter(pk=p.pk).update(contenido_litros=0)
