"""T7, T9 a T12: casos de uso de productos con un inventario falso (RF-CAT-04 a 13, 19 a 21)."""

from decimal import Decimal

import pytest

from catalog.application import productos as uc
from catalog.domain.errores import (
    CampoInmutable,
    LimiteProductosPlan,
    NoSePuedeDesactivar,
    NoSePuedeEliminar,
)
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_uso, catalogo_query
from catalog.infrastructure.models import Producto
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado

pytestmark = pytest.mark.django_db
MALTA = DatosProducto("INS-MALTA", "Malta Pilsen", T.INSUMO, "KG")


def crear(actor, datos=MALTA):
    return caso_de_uso(uc.CrearProducto).ejecutar(actor, datos)


def test_con_movimientos_no_cambian_sku_tipo_unidad_pero_si_el_nombre(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    malta = crear(actor)
    inventario.con_movimientos.add(malta)
    editar = caso_de_uso(uc.EditarProducto)
    for cambio in ({"sku": "INS-M2"}, {"tipo": T.ENVASE}, {"unidad": "G"}):
        with pytest.raises(CampoInmutable, match="No se puede modificar SKU, tipo o unidad"):
            editar.ejecutar(actor, malta, DatosProducto(**{**MALTA.__dict__, **cambio}))
    editar.ejecutar(
        actor,
        malta,
        DatosProducto(**{**MALTA.__dict__, "nombre": "Malta Viena", "stock_minimo": Decimal("10")}),
    )
    assert Producto.objects.get(pk=malta).nombre == "Malta Viena"


def test_limite_de_productos_del_plan(empresa_catalogo, inventario):
    empresa, actor = empresa_catalogo
    empresa.plan.limite_productos = 2
    empresa.plan.save()
    a = crear(actor)
    crear(actor, DatosProducto("ENV-BOT", "Botella", T.ENVASE, "UND"))
    with pytest.raises(LimiteProductosPlan, match="Tu plan permite hasta 2 productos activos"):
        crear(actor, DatosProducto("ENV-TAPA", "Tapa", T.ENVASE, "UND"))
    caso_de_uso(uc.CambiarEstadoProducto).ejecutar(actor, a, False)
    crear(actor, DatosProducto("ENV-TAPA", "Tapa", T.ENVASE, "UND"))
    with pytest.raises(LimiteProductosPlan):
        caso_de_uso(uc.CambiarEstadoProducto).ejecutar(actor, a, True)


def test_desactivar_y_eliminar(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    malta = crear(actor)
    inventario.stocks[malta] = Decimal("25")
    estado = caso_de_uso(uc.CambiarEstadoProducto)
    with pytest.raises(NoSePuedeDesactivar, match="Ajusta el stock a cero"):
        estado.ejecutar(actor, malta, False)
    with pytest.raises(NoSePuedeEliminar, match="El producto tiene historial"):
        caso_de_uso(uc.EliminarProducto).ejecutar(actor, malta)
    inventario.stocks[malta] = Decimal("0")
    estado.ejecutar(actor, malta, False)
    assert catalogo_query().producto(malta).activo is False  # sigue en el historial
    assert malta not in [p.id for p in catalogo_query().activos()]
    botella = crear(actor, DatosProducto("ENV-BOT", "Botella", T.ENVASE, "UND"))
    caso_de_uso(uc.EliminarProducto).ejecutar(actor, botella)
    assert not Producto.objects.filter(pk=botella).exists()


def test_mercaderia_comprable_y_vendible(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    agua = crear(
        actor,
        DatosProducto(
            "MER-AGUA",
            "Agua 500 ml",
            T.MERCADERIA,
            "UND",
            precio_venta=Decimal("3.00"),
            controla_lote=True,
            vida_util_dias=365,
        ),
    )
    dto = catalogo_query().producto(agua)
    assert dto.tipo.comprable and dto.tipo.vendible and dto.controla_lote
    assert [p.id for p in catalogo_query().activos([T.MERCADERIA])] == [agua]


def test_sin_permiso_se_rechaza(empresa_catalogo):
    empresa, _ = empresa_catalogo
    with pytest.raises(AccesoDenegado):
        crear(Actor(1, empresa.id, frozenset({"catalogo.producto.ver"})))
