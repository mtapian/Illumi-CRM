"""T1 a T4: productos por tipo (RF-CAT-04 a 13, 20, 21; RN-CAT-01 a 03, 06, 07, 09)."""

from decimal import Decimal

import pytest

from catalog.domain.errores import ProductoInvalido
from catalog.domain.producto import (
    DatosProducto,
    cabe_en_limite,
    cambios_prohibidos,
    campos_requeridos,
    puede_desactivar,
    puede_eliminar,
    validar_producto,
)
from catalog.domain.tipos import TipoProducto as T


def datos(tipo, **kw):
    base = {"sku": "X-1", "nombre": "X", "tipo": T(tipo), "unidad": "UND"}
    return DatosProducto(**(base | kw))


def test_capacidades_de_cada_tipo():
    assert {t for t in T if t.vendible} == {T.TERMINADO, T.MERCADERIA}
    assert {t for t in T if t.comprable} == {T.INSUMO, T.ENVASE, T.MERCADERIA}
    assert {t for t in T if t.producible} == {T.GRANEL, T.TERMINADO}
    assert {t for t in T if t.lote_siempre} == {T.GRANEL, T.TERMINADO}


def test_campos_propios_de_cada_tipo():
    assert "precio_venta" not in campos_requeridos(T.INSUMO)
    assert {"precio_venta", "vida_util_dias"} <= campos_requeridos(T.TERMINADO)
    assert {"precio_venta", "controla_lote", "contenido_litros"} <= campos_requeridos(T.MERCADERIA)
    assert {"vida_util_dias", "prefijo_lote"} <= campos_requeridos(T.GRANEL)


def test_normaliza_el_lote_y_descarta_campos_ajenos_al_tipo():
    granel = validar_producto(datos("GRANEL", nombre="IPA a granel", unidad="L"))
    assert granel.controla_lote and granel.prefijo_lote == "IPA"
    insumo = validar_producto(datos("INSUMO", precio_venta=Decimal("5"), controla_lote=True))
    assert insumo.precio_venta is None and not insumo.controla_lote
    agua = validar_producto(
        datos("MERCADERIA", precio_venta=Decimal("3"), controla_lote=True, vida_util_dias=365)
    )
    assert agua.controla_lote


@pytest.mark.parametrize(
    "producto, mensaje",
    [
        (datos("GRANEL", unidad="KG"), "El granel debe medirse en litros"),
        (datos("TERMINADO", precio_venta=Decimal("12")), "La vida útil debe ser mayor a 0 días"),
        (
            datos("TERMINADO", precio_venta=Decimal("12"), vida_util_dias=0),
            "La vida útil debe ser mayor a 0 días",
        ),
        (datos("MERCADERIA"), "El precio de venta es obligatorio"),
        (
            datos("MERCADERIA", precio_venta=Decimal("3"), controla_lote=True),
            "Indica la vida útil sugerida",
        ),
        (datos("INSUMO", sku=" "), "El SKU es obligatorio"),
    ],
)
def test_rechazos(producto, mensaje):
    with pytest.raises(ProductoInvalido, match=mensaje):
        validar_producto(producto)


def test_con_movimientos_no_cambian_sku_tipo_unidad_ni_lote():
    original = validar_producto(datos("INSUMO", unidad="KG"))
    nuevo = validar_producto(datos("INSUMO", unidad="G", sku="X-2", nombre="Otro"))
    assert cambios_prohibidos(original, nuevo, tiene_movimientos=True) == ["sku", "unidad"]
    assert cambios_prohibidos(original, nuevo, tiene_movimientos=False) == []


def test_limite_desactivar_y_eliminar():
    assert cabe_en_limite(49, 50) and not cabe_en_limite(50, 50) and cabe_en_limite(9, None)
    assert puede_desactivar(Decimal("0"), granel_con_presentaciones=False) is None
    assert "stock" in puede_desactivar(Decimal("25"), granel_con_presentaciones=False)
    assert "presentaciones" in puede_desactivar(Decimal("0"), granel_con_presentaciones=True)
    assert puede_eliminar(tiene_movimientos=False, referencias=0)
    assert not puede_eliminar(tiene_movimientos=True, referencias=0)
    assert not puede_eliminar(tiene_movimientos=False, referencias=1)
