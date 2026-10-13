"""0002a enmienda 4, T31: Bien o Servicio y casillas de gestión (RF-CAT-37 a 40, 42, 43;
RF-CAT-08, 10, 21)."""

from decimal import Decimal

import pytest

from catalog.domain.errores import ProductoInvalido
from catalog.domain.producto import (
    DatosProducto,
    cabe_en_limite,
    cambios_prohibidos,
    puede_desactivar,
    puede_eliminar,
    validar_producto,
)
from catalog.domain.tipos import TipoProducto as T


def datos(tipo=T.BIEN, **kw):
    base = {"sku": "X-1", "nombre": "X", "tipo": T(tipo), "unidad": "UND"}
    return DatosProducto(**(base | kw))


def test_un_bien_nuevo_se_compra_por_defecto_y_normaliza_textos():
    d = validar_producto(datos(sku=" ins-1 ", nombre=" Malta ", codigo_barras=" 775 "))
    assert (d.se_compra, d.se_vende, d.se_fabrica) == (True, False, False)
    assert (d.sku, d.nombre, d.codigo_barras) == ("INS-1", "Malta", "775")


def test_si_no_se_vende_se_descartan_precio_y_litros():
    d = validar_producto(datos(precio_venta=Decimal("5"), contenido_litros=Decimal("1")))
    assert (d.precio_venta, d.contenido_litros) == (None, None)


def test_un_servicio_no_lleva_inventario():
    d = validar_producto(
        datos(
            T.SERVICIO,
            se_compra=False,
            se_vende=True,
            precio_venta=Decimal("8"),
            stock_minimo=Decimal("5"),
            vida_util_dias=10,
            peso_kg=Decimal("1"),
            volumen_m3=Decimal("1"),
            contenido_litros=Decimal("1"),
        )
    )
    assert d.stock_minimo == 0
    assert (d.vida_util_dias, d.peso_kg, d.volumen_m3, d.contenido_litros) == (None,) * 4


def test_peso_volumen_y_vida_util_son_opcionales():
    d = validar_producto(datos(peso_kg=Decimal("25"), volumen_m3=Decimal("0.04")))
    assert (d.peso_kg, d.volumen_m3, d.vida_util_dias) == (Decimal("25"), Decimal("0.04"), None)


@pytest.mark.parametrize(
    "producto, mensaje",
    [
        (datos(se_compra=False), "Marca al menos una opción: se vende, se compra o se fabrica"),
        (datos(T.SERVICIO, se_fabrica=True), "Un servicio no se fabrica"),
        (datos(se_vende=True), "El precio de venta es obligatorio y debe ser mayor a 0"),
        (datos(vida_util_dias=0), "La vida útil debe ser mayor a 0 días"),
        (datos(peso_kg=Decimal("-1")), "El peso no puede ser negativo"),
        (datos(volumen_m3=Decimal("-1")), "El volumen no puede ser negativo"),
        (datos(sku=" "), "El SKU es obligatorio"),
    ],
)
def test_rechazos(producto, mensaje):
    with pytest.raises(ProductoInvalido, match=mensaje):
        validar_producto(producto)


def test_con_movimientos_no_cambian_tipo_sku_ni_unidad_pero_si_las_casillas():
    original = validar_producto(datos(unidad="KG"))
    nuevo = validar_producto(
        datos(T.SERVICIO, unidad="G", sku="X-2", se_vende=True, precio_venta=Decimal("1"))
    )
    assert cambios_prohibidos(original, nuevo, tiene_movimientos=True) == [
        "sku",
        "tipo",
        "unidad",
    ]
    casillas = validar_producto(datos(unidad="KG", se_vende=True, precio_venta=Decimal("2")))
    assert cambios_prohibidos(original, casillas, tiene_movimientos=True) == []


def test_limite_desactivar_y_eliminar():
    assert cabe_en_limite(49, 50) and not cabe_en_limite(50, 50) and cabe_en_limite(9, None)
    assert puede_desactivar(Decimal("0")) is None
    assert "stock" in puede_desactivar(Decimal("25"))
    assert puede_eliminar(tiene_movimientos=False, referencias=0)
    assert not puede_eliminar(tiene_movimientos=True, referencias=0)
    assert not puede_eliminar(tiene_movimientos=False, referencias=1)


def test_estrategia_de_salida_fefo_por_defecto_y_servicio_sin_ella():
    """0002a enmienda 6, RF-CAT-62."""
    assert validar_producto(datos()).estrategia_salida == "FEFO"
    assert validar_producto(datos(estrategia_salida="FIFO")).estrategia_salida == "FIFO"
    servicio = datos(
        T.SERVICIO,
        se_compra=False,
        se_vende=True,
        precio_venta=Decimal("8"),
        estrategia_salida="FIFO",
    )
    assert validar_producto(servicio).estrategia_salida == "FEFO"
    with pytest.raises(ProductoInvalido, match="La estrategia de salida debe ser FEFO o FIFO"):
        validar_producto(datos(estrategia_salida="LIFO"))
