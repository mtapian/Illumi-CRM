"""0005a, T5: finalizar una OP con el ejemplo de la spec (RF-PRD-09, 14, 15, 41, 42, 46, 47)."""

from dataclasses import replace
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
from production.domain.op import Componente, Salida
from production.infrastructure.contenedor import caso_de_op
from production.infrastructure.models import OpComponente, OpSalida, OrdenProduccion

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
    datos = uc.DatosOp((Salida(ids[sku], D(cantidad)),), HOY, almacen, almacen)
    op_id = caso_de_op(uc.CrearOp).ejecutar(actor, datos)
    caso_de_op(uc.PasarAEnProceso).ejecutar(actor, op_id)
    return op_id


def finalizar(ej, op_id, producida, consumos=(), **kw):
    """Finaliza una OP de una sola salida; sus componentes vienen de su receta (asignados)."""
    actor, _, ids = ej
    salida = OpSalida.objects.filter(op_id=op_id).order_by("id").first().producto_id
    reales = tuple(uc.ConsumoReal(ids[s], D(q), lote, salida) for s, q, lote in consumos)
    f = uc.Finalizacion((uc.Producido(salida, D(producida)),), HOY, reales, **kw)
    return caso_de_op(uc.FinalizarOp).ejecutar(actor, op_id, f, HOY)


def resumen(op_id):
    """La OP y su (primera) salida."""
    return OrdenProduccion.objects.get(pk=op_id), OpSalida.objects.filter(op_id=op_id).first()


def stock(ids, sku, lote=None):
    filas = Stock.objects.filter(producto_id=ids[sku])
    if lote:
        filas = filas.filter(lote__codigo=lote)
    return sum(s.cantidad for s in filas)


def test_granel_y_envasado_del_ejemplo_de_la_spec(ej):
    _, _, ids = ej
    granel = op_en_proceso(ej, "GRA-IPA", "500")
    assert finalizar(ej, granel, "425", [("INS-MALTA", "102", None)], costo_indirecto=D("52")) == []
    op, s = resumen(granel)
    assert (op.estado, s.lote_codigo, op.costo_total, s.costo_unitario) == (
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
    op, s = resumen(envasado)
    assert (s.lote_codigo, op.costo_total, s.costo_unitario) == (
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
    op, s = resumen(op_id)
    assert (op.perdida, s.lote_codigo, s.costo_unitario) == (D("790.00"), "", None)
    assert not Lote.objects.filter(producto_id=ids["GRA-IPA"]).exists()
    assert stock(ids, "INS-MALTA") == D("200")
    otra = op_en_proceso(ej, "GRA-IPA", "100")  # cabe en lo que quedó tras el lote perdido
    assert finalizar(ej, otra, "110") == ["Rendimiento mayor a 100 %"]


def test_solo_desde_en_proceso_y_con_producto_que_se_fabrica(ej):
    """RF-PRD-33 y RF-PRD-47."""
    actor, almacen, ids = ej
    creada = caso_de_op(uc.CrearOp).ejecutar(
        actor, uc.DatosOp((Salida(ids["GRA-IPA"], D("1")),), HOY, almacen, almacen)
    )
    with pytest.raises(OpInvalida, match="La OP debe estar en proceso para finalizarla"):
        finalizar(ej, creada, "1")
    op_id = op_en_proceso(ej, "GRA-IPA", "500")
    Producto.objects.filter(pk=ids["GRA-IPA"]).update(
        se_fabrica=False, se_vende=True, precio_venta=1
    )
    with pytest.raises(OpInvalida, match="El producto ya no está activo o ya no se fabrica"):
        finalizar(ej, op_id, "425")


def test_sin_componentes_el_costo_es_el_indirecto(ej):
    """RF-PRD-47 (PO, 2026-10-12): los componentes no son obligatorios."""
    actor, almacen, ids = ej
    datos = uc.DatosOp((Salida(ids["GRA-IPA"], D("10")),), HOY, almacen, almacen)
    sin = caso_de_op(uc.CrearOp).ejecutar(actor, datos, usar_receta=False)
    caso_de_op(uc.PasarAEnProceso).ejecutar(actor, sin)
    finalizar(ej, sin, "10", costo_indirecto=D("30"))
    op, s = resumen(sin)
    assert (op.estado, op.costo_total, s.costo_unitario) == (
        "FINALIZADA",
        D("30.00"),
        D("3.000000"),
    )
    assert not Movimiento.objects.filter(ref_id=sin, tipo="SALIDA").exists()
    otra = caso_de_op(uc.CrearOp).ejecutar(actor, datos, usar_receta=False)
    caso_de_op(uc.PasarAEnProceso).ejecutar(actor, otra)
    finalizar(ej, otra, "10")
    assert resumen(otra)[1].costo_unitario == D("0.000000")


def test_envasado_en_dos_presentaciones_del_ejemplo_de_la_enmienda(ej):
    """Enmienda 1, RF-PRD-49 a 52: receta por salida, servicio común repartido por factor,
    un lote por producto (el del granel que consumen)."""
    actor, almacen, ids = ej
    und = Unidad.objects.get(abreviatura="UND")
    ids["ENV-PREC"] = Producto.objects.create(sku="ENV-PREC", nombre="Precinto", unidad=und).id
    ids["SRV-LIMP"] = Producto.objects.create(
        sku="SRV-LIMP",
        nombre="Limpieza",
        tipo="SERVICIO",
        se_compra=True,
        unidad=Unidad.objects.get(abreviatura="SERV"),
    ).id
    barril = Producto.objects.create(
        sku="TER-IPA-20L",
        nombre="IPA barril",
        unidad=und,
        se_compra=False,
        se_fabrica=True,
        se_vende=True,
        precio_venta=300,
    )
    ids["TER-IPA-20L"] = barril.id
    for componente, q in (("GRA-IPA", "20"), ("ENV-PREC", "1")):
        RecetaComponente.objects.create(
            producto=barril, componente_id=ids[componente], cantidad_por_unidad=D(q)
        )
    with transaction.atomic():
        inventario().registrar_entrada(
            "COMPRA",
            "COMPRA",
            2,
            [
                Linea(ids["GRA-IPA"], almacen, D("425"), D("2"), "IPA-0020"),
                Linea(ids["ENV-PREC"], almacen, D("10"), D("1.5")),
            ],
            actor.usuario_id,
            HOY,
        )
    salidas = (
        Salida(ids["TER-IPA-330"], D("1000"), D("0.33")),
        Salida(ids["TER-IPA-20L"], D("3"), D("20")),
    )
    datos = uc.DatosOp(salidas, HOY, almacen, almacen)
    op_id = caso_de_op(uc.CrearOp).ejecutar(actor, datos)
    actual = list(OpComponente.objects.filter(op_id=op_id).select_related("salida"))
    assert {(c.producto_id, c.salida.producto_id) for c in actual} >= {
        (ids["GRA-IPA"], ids["TER-IPA-330"]),
        (ids["GRA-IPA"], ids["TER-IPA-20L"]),
    }  # el granel en las dos salidas (RF-PRD-50)
    lista = tuple(
        Componente(c.producto_id, c.por_consumir, c.costo_servicio, c.salida.producto_id)
        for c in actual
    ) + (Componente(ids["SRV-LIMP"], D("1"), D("39")),)  # común (RF-PRD-51)
    caso_de_op(uc.EditarOp).ejecutar(actor, op_id, replace(datos, componentes=lista))
    caso_de_op(uc.PasarAEnProceso).ejecutar(actor, op_id)
    f = uc.Finalizacion((), HOY)  # lo programado y lo por consumir
    caso_de_op(uc.FinalizarOp).ejecutar(actor, op_id, f, HOY)
    filas = {s.producto_id: s for s in OpSalida.objects.filter(op_id=op_id)}
    botella, barriles = filas[ids["TER-IPA-330"]], filas[ids["TER-IPA-20L"]]
    assert (botella.costo_total, botella.costo_unitario, botella.lote_codigo) == (
        D("1893.08"),
        D("1.893080"),
        "IPA-0020",
    )
    assert (barriles.costo_total, barriles.costo_unitario, barriles.lote_codigo) == (
        D("130.50"),
        D("43.500000"),
        "IPA-0020",
    )
    assert OrdenProduccion.objects.get(pk=op_id).costo_total == D("2023.58")
    assert stock(ids, "GRA-IPA", "IPA-0020") == D("35")
    assert stock(ids, "TER-IPA-20L", "IPA-0020") == D("3")
