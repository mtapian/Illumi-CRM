"""0002a, T24, T25, T42 y T43: marcas, categorías y edición de unidades (RF-CAT-33 a 35, 49, 50)."""

import pytest

from catalog.application import productos as uc
from catalog.domain.errores import AgrupacionInvalida, ProductoInvalido, UnidadInvalida
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_uso
from catalog.infrastructure.models import Categoria, Marca, Producto, Unidad

pytestmark = pytest.mark.django_db


def guardar(actor, tipo, nombre, id_=None, **kw):
    return caso_de_uso(uc.GuardarAgrupacion).ejecutar(actor, tipo, id_, nombre, **kw)


@pytest.mark.parametrize("tipo", ["marca", "categoria"])
def test_nombre_unico_sin_mayusculas_y_editable(empresa_catalogo, tipo):
    _, actor = empresa_catalogo
    gloria = guardar(actor, tipo, "Gloria")
    with pytest.raises(AgrupacionInvalida, match=f"Ya existe la {uc.NOMBRE[tipo]} gloria"):
        guardar(actor, tipo, "gloria")
    guardar(actor, tipo, "Gloria SA", gloria)
    modelo = Marca if tipo == "marca" else Categoria
    assert modelo.objects.get(pk=gloria).nombre == "Gloria SA"
    with pytest.raises(AgrupacionInvalida, match="obligatorio"):
        guardar(actor, tipo, "  ")


def test_categoria_guarda_descripcion_opcional(empresa_catalogo):
    """RF-CAT-50: descripción opcional, texto libre."""
    _, actor = empresa_catalogo
    cat = guardar(actor, "categoria", "Lúpulos", descripcion="Variedades aromáticas y amargor")
    assert Categoria.objects.get(pk=cat).descripcion == "Variedades aromáticas y amargor"


@pytest.mark.parametrize("tipo", ["marca", "categoria"])
def test_en_uso_no_se_elimina_pero_se_desactiva(empresa_catalogo, inventario, tipo):
    _, actor = empresa_catalogo
    usada, libre = guardar(actor, tipo, "Gloria"), guardar(actor, tipo, "Nestlé")
    caso_de_uso(uc.CrearProducto).ejecutar(
        actor, DatosProducto("INS-M", "Malta", T.BIEN, "KG", **{f"{tipo}_id": usada})
    )
    with pytest.raises(
        AgrupacionInvalida, match=f"La {uc.NOMBRE[tipo]} está en uso; puedes desactivarla"
    ):
        caso_de_uso(uc.EliminarAgrupacion).ejecutar(actor, tipo, usada)
    caso_de_uso(uc.EliminarAgrupacion).ejecutar(actor, tipo, libre)
    caso_de_uso(uc.CambiarEstadoAgrupacion).ejecutar(actor, tipo, usada, False)
    assert getattr(Producto.objects.get(sku="INS-M"), f"{tipo}_id") == usada  # la conserva
    with pytest.raises(ProductoInvalido, match=f"La {uc.NOMBRE[tipo]} no existe o está inactiva"):
        caso_de_uso(uc.CrearProducto).ejecutar(
            actor, DatosProducto("INS-N", "Otra", T.BIEN, "KG", **{f"{tipo}_id": usada})
        )


def test_editar_unidad_en_uso_bloquea_la_abreviatura(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    caso_de_uso(uc.CrearProducto).ejecutar(actor, DatosProducto("INS-M", "M", T.BIEN, "KG"))
    kg = Unidad.objects.get(abreviatura="KG").id
    editar = caso_de_uso(uc.EditarUnidad)
    with pytest.raises(UnidadInvalida, match="su abreviatura no se puede cambiar"):
        editar.ejecutar(actor, kg, "Kilo", "KILO", "KGM")
    editar.ejecutar(actor, kg, "Kilo", "KG", "KGM")
    assert Unidad.objects.get(pk=kg).nombre == "Kilo"
    ml = Unidad.objects.get(abreviatura="ML").id
    editar.ejecutar(actor, ml, "Mililitro", "mlt", "MLT")  # libre: se puede cambiar
    assert Unidad.objects.get(pk=ml).abreviatura == "MLT"
    with pytest.raises(UnidadInvalida, match="Ya existe la unidad KG"):
        editar.ejecutar(actor, ml, "X", "KG", "MLT")


def test_categoria_con_descripcion_y_estado_en_su_formulario(empresa_catalogo):
    """RF-CAT-50: nombre, descripción opcional y "Categoría activa", en una sola operación."""
    _, actor = empresa_catalogo
    abarrotes = guardar(actor, "categoria", "Abarrotes", descripcion=" Secos ", activo=True)
    guardar(actor, "categoria", "Abarrotes", abarrotes, descripcion="", activo=False)
    c = Categoria.objects.get(pk=abarrotes)
    assert (c.nombre, c.descripcion, c.activo) == ("Abarrotes", "", False)
    marca = guardar(actor, "marca", "Gloria")
    assert Marca.objects.get(pk=marca).activo  # sin `activo` no cambia el estado
