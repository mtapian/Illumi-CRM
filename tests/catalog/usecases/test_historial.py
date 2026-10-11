"""0002a, T19 y T20: código de barras, historial y cambio de tipo (RF-CAT-29, 31, 32)."""

from dataclasses import replace
from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction

from catalog.application import productos as uc
from catalog.domain.errores import CampoInmutable, CodigoBarrasDuplicado
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import caso_de_uso
from catalog.infrastructure.models import Producto
from catalog.infrastructure.repositorios import CatalogoOrm

pytestmark = pytest.mark.django_db
MALTA = DatosProducto("INS-MALTA", "Malta Pilsen", T.BIEN, "KG", codigo_barras="775000000001")


def crear(actor, datos=MALTA, receta=None):
    return caso_de_uso(uc.CrearProducto).ejecutar(actor, datos, receta)


def editar(actor, producto_id, datos, receta=None):
    caso_de_uso(uc.EditarProducto).ejecutar(actor, producto_id, datos, receta)


def test_codigo_barras_unico_por_empresa_y_vacio_permitido(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    crear(actor)
    with pytest.raises(CodigoBarrasDuplicado, match="ya está asignado a INS-MALTA"):
        crear(actor, DatosProducto("INS-LUP", "Lúpulo", T.BIEN, "KG", codigo_barras="775000000001"))
    crear(actor, DatosProducto("INS-A", "A", T.BIEN, "KG", referencia="Proveedor X"))
    crear(actor, DatosProducto("INS-B", "B", T.BIEN, "KG"))
    assert Producto.objects.filter(codigo_barras="").count() == 2


def test_historial_de_creacion_edicion_y_estado(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    malta = crear(actor)
    editar(actor, malta, replace(MALTA, nombre="Malta Viena", stock_minimo=Decimal("10")))
    caso_de_uso(uc.CambiarEstadoProducto).ejecutar(actor, malta, False)
    filas = CatalogoOrm().historial(malta)  # del más reciente al más antiguo
    assert [f.accion for f in filas] == ["desactivado", "editado", "creado"]
    assert filas[0].cambios == ["activo: sí → no"]
    assert filas[1].cambios == ["nombre: Malta Pilsen → Malta Viena", "stock_minimo: 0 → 10"]
    assert filas[2].autor == "lucia@andina.pe" and filas[2].cambios == []
    editar(actor, malta, replace(MALTA, nombre="Malta Viena", stock_minimo=Decimal("10")))
    assert len(CatalogoOrm().historial(malta)) == 3  # guardar sin cambios no registra nada


def test_historial_no_se_edita_ni_se_borra(empresa_catalogo, inventario):
    _, actor = empresa_catalogo
    crear(actor)
    for sql in (
        "UPDATE catalog_productohistorial SET accion='x'",
        "DELETE FROM catalog_productohistorial",
    ):
        with pytest.raises(DatabaseError), transaction.atomic():
            _ejecutar(sql)


def _ejecutar(sql):
    with connection.cursor() as c:
        c.execute(sql)


def test_cambiar_de_bien_a_servicio_sin_movimientos(empresa_catalogo, inventario):
    """RF-CAT-43 (reemplaza RF-CAT-29)."""
    _, actor = empresa_catalogo
    malta = crear(actor)
    servicio = replace(
        MALTA, tipo=T.SERVICIO, unidad="SERV", se_vende=True, precio_venta=Decimal(1)
    )
    editar(actor, malta, servicio)
    assert Producto.objects.get(pk=malta).tipo == T.SERVICIO
    assert "tipo: BIEN → SERVICIO" in CatalogoOrm().historial(malta)[0].cambios
    inventario.con_movimientos.add(malta)
    with pytest.raises(CampoInmutable):
        editar(actor, malta, replace(MALTA, unidad="SERV"))
