"""0005a, T5: finalizar una OP con el ejemplo de la spec (RF-PRD-09, 14, 15, 41, 42, 46, 47)."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from django.db import transaction

from catalog.infrastructure.models import Producto, RecetaComponente, Unidad
from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen, Lote, Movimiento, Stock
from production.application import ordenes as uc
from production.domain.errores import OpInvalida
from production.infrastructure.contenedor import caso_de_op
from production.infrastructure.models import OpComponente, OrdenProduccion

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 12)


@pytest.fixture
def ej(empresa_produccion):
    """Insumos con stock y costo, GRA-IPA con su receta por litro y TER-IPA-330 (envasado)."""
    _, actor = empresa_produccion
    almacen = Almacen.objects.get(nombre="Principal").id
    u = {a: Unidad.objects.get(abreviatura=a) for a in ("KG", "G", "UND", "L")}
    ids = {"GRA-IPA": Producto.objects.get(sku="GRA-IPA").id}
    ids["INS-MALTA"] = Producto.objects.get(sku="INS-MALTA").id
    for sku, unidad in [
        ("INS-MALTA-CAR", "KG"),
        ("INS-LUP-CS", "G"),
        ("INS-LEV-US05", "UND"),
        ("ENV-BOT330", "UND"),
        ("ENV-TAPA", "UND"),
        ("ENV-ETQ", "UND"),
        ("ENV-CAJA24", "UND"),
    ]:
        ids[sku] = Producto.objects.create(sku=sku, nombre=sku, unidad=u[unidad]).id
    ids["TER-IPA-330"] = Producto.objects.create(
        sku="TER-IPA-330",
        nombre="IPA 330",
        unidad=u["UND"],
        se_compra=False,
        se_fabrica=True,
        se_vende=True,
        precio_venta=12,
    ).id

    def receta(producto, filas):
        for componente, q in filas:
            RecetaComponente.objects.create(
                producto_id=ids[producto], componente_id=ids[componente], cantidad_por_unidad=D(q)
            )

    receta(
        "GRA-IPA",
        [
            ("INS-MALTA", "0.2"),
            ("INS-MALTA-CAR", "0.02"),
            ("INS-LUP-CS", "3"),
            ("INS-LEV-US05", "0.02"),
        ],
    )
    receta(
        "TER-IPA-330",
        [
            ("GRA-IPA", "0.33"),
            ("ENV-BOT330", "1"),
            ("ENV-TAPA", "1"),
            ("ENV-ETQ", "1"),
            ("ENV-CAJA24", "0.0417"),
        ],
    )
    stock = [
        ("INS-MALTA", "300", "4"),
        ("INS-MALTA-CAR", "15", "6"),
        ("INS-LUP-CS", "4000", "0.12"),
        ("INS-LEV-US05", "12", "15"),
        ("ENV-BOT330", "2000", "0.85"),
        ("ENV-TAPA", "2000", "0.05"),
        ("ENV-ETQ", "2000", "0.2"),
        ("ENV-CAJA24", "100", "2.4"),
    ]
    lineas = [Linea(ids[s], almacen, D(q), D(c)) for s, q, c in stock]
    with transaction.atomic():  # también en los tests con transacciones reales
        inventario().registrar_entrada("COMPRA", "COMPRA", 1, lineas, actor.usuario_id, HOY)
    return actor, almacen, ids


def op_en_proceso(ej, sku, cantidad):
    actor, almacen, ids = ej
    datos = uc.DatosOp(ids[sku], D(cantidad), HOY, almacen, almacen)
    op_id = caso_de_op(uc.CrearOp).ejecutar(actor, datos)
    caso_de_op(uc.PasarAEnProceso).ejecutar(actor, op_id)
    return op_id


def finalizar(ej, op_id, producida, consumos=(), **kw):
    actor, _, ids = ej
    reales = tuple(uc.ConsumoReal(ids[s], D(q), lote) for s, q, lote in consumos)
    f = uc.Finalizacion(D(producida), HOY, reales, **kw)
    return caso_de_op(uc.FinalizarOp).ejecutar(actor, op_id, f, HOY)


def stock(ids, sku, lote=None):
    filas = Stock.objects.filter(producto_id=ids[sku])
    if lote:
        filas = filas.filter(lote__codigo=lote)
    return sum(s.cantidad for s in filas)


def test_granel_y_envasado_del_ejemplo_de_la_spec(ej):
    _, _, ids = ej
    granel = op_en_proceso(ej, "GRA-IPA", "500")
    assert finalizar(ej, granel, "425", [("INS-MALTA", "102", None)], costo_indirecto=D("52")) == []
    op = OrdenProduccion.objects.get(pk=granel)
    assert (op.estado, op.lote_codigo, op.costo_total, op.costo_unitario) == (
        "FINALIZADA",
        "GRA-IPA-0001",
        D("850.00"),
        D("2.000000"),
    )
    assert stock(ids, "INS-MALTA") == D("198")
    lote = Lote.objects.get(producto_id=ids["GRA-IPA"])
    assert (lote.codigo, lote.fecha_vencimiento) == ("GRA-IPA-0001", HOY + timedelta(days=60))
    malta = OpComponente.objects.get(op_id=granel, producto_id=ids["INS-MALTA"])
    assert (malta.consumido, malta.costo) == (D("102.0000"), D("408.00"))

    envasado = op_en_proceso(ej, "TER-IPA-330", "1000")
    finalizar(ej, envasado, "1000", [("GRA-IPA", "340", None)])
    op = OrdenProduccion.objects.get(pk=envasado)
    assert (op.lote_codigo, op.costo_total, op.costo_unitario) == (
        "GRA-IPA-0001",
        D("1880.08"),
        D("1.880080"),
    )  # hereda el lote del granel (RF-PRD-46)
    assert stock(ids, "TER-IPA-330", "GRA-IPA-0001") == D("1000")
    assert stock(ids, "GRA-IPA") == D("85")
    fechas = {m.fecha.date() for m in Movimiento.objects.filter(ref_tipo="OP")}
    assert len(fechas) == 1


def test_faltantes_de_todos_sin_movimientos(ej):
    """RF-PRD-09."""
    op_id = op_en_proceso(ej, "GRA-IPA", "500")
    antes = Movimiento.objects.count()
    with pytest.raises(OpInvalida, match="Stock insuficiente: INS-LEV-US05 faltan 1.0000"):
        finalizar(ej, op_id, "425", [("INS-LEV-US05", "13", None)])
    assert Movimiento.objects.count() == antes
    assert OrdenProduccion.objects.get(pk=op_id).estado == "EN_PROCESO"


def test_lote_perdido_y_rendimiento_mayor(ej):
    """RF-PRD-15 y 14."""
    _, _, ids = ej
    op_id = op_en_proceso(ej, "GRA-IPA", "500")
    with pytest.raises(OpInvalida, match="Indica el motivo del lote perdido"):
        finalizar(ej, op_id, "0")
    finalizar(ej, op_id, "0", motivo_perdida="Contaminación")
    op = OrdenProduccion.objects.get(pk=op_id)
    assert (op.perdida, op.lote_codigo, op.costo_unitario) == (D("790.00"), "", None)
    assert not Lote.objects.filter(producto_id=ids["GRA-IPA"]).exists()
    assert stock(ids, "INS-MALTA") == D("200")
    otra = op_en_proceso(ej, "GRA-IPA", "100")  # cabe en lo que quedó tras el lote perdido
    assert finalizar(ej, otra, "110") == ["Rendimiento mayor a 100 %"]


def test_solo_desde_en_proceso_y_con_producto_que_se_fabrica(ej):
    """RF-PRD-33 y RF-PRD-47."""
    actor, almacen, ids = ej
    creada = caso_de_op(uc.CrearOp).ejecutar(
        actor, uc.DatosOp(ids["GRA-IPA"], D("1"), HOY, almacen, almacen)
    )
    with pytest.raises(OpInvalida, match="La OP debe estar en proceso para finalizarla"):
        finalizar(ej, creada, "1")
    op_id = op_en_proceso(ej, "GRA-IPA", "500")
    Producto.objects.filter(pk=ids["GRA-IPA"]).update(
        se_fabrica=False, se_vende=True, precio_venta=1
    )
    with pytest.raises(OpInvalida, match="El producto ya no está activo o ya no se fabrica"):
        finalizar(ej, op_id, "425")
