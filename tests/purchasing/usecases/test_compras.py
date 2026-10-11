"""0004a, T3 a T5: crear, editar, pasar a en proceso y finalizar la compra (RF-COM-04 a 12,
19, 23 a 27)."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from django.utils import timezone

from catalog.infrastructure.models import Producto, Unidad
from inventory.domain.errores import LoteConOtroVencimiento
from inventory.infrastructure.models import Almacen, CostoProducto, Lote, Movimiento, Stock
from purchasing.application import compras as uc
from purchasing.application.compras import DatosCompra
from purchasing.application.puertos import puertos
from purchasing.domain.compra import LineaCompra
from purchasing.domain.errores import CompraInvalida
from purchasing.infrastructure.contenedor import caso_de_compra
from purchasing.infrastructure.models import Compra, Proveedor
from shared.domain.errores import NoEncontrado

pytestmark = pytest.mark.django_db
HOY = timezone.localdate()


@pytest.fixture
def base(empresa_compras):
    _, actor = empresa_compras
    proveedor = Proveedor.objects.create(
        tipo_doc="RUC", num_doc="20512345671", razon_social="Maltería del Sur"
    )
    return {
        "actor": actor,
        "proveedor": proveedor.id,
        "principal": Almacen.objects.get().id,
        "malta": Producto.objects.get(sku="INS-MALTA").id,
    }


def datos(b, lineas=None, doc="FACTURA", serie="F001-000845", **kw):
    if lineas is None:
        lineas = [LineaCompra(b["malta"], D("50"), D("5.00"))]
    campos = {"proveedor_id": b["proveedor"], "fecha": HOY, "almacen_id": b["principal"]}
    return DatosCompra(**(campos | kw), doc_tipo=doc, doc_serie_numero=serie, lineas=lineas)


def crear(b, **kw):
    return caso_de_compra(uc.CrearCompra).ejecutar(b["actor"], datos(b, **kw))


def finalizar(b, compra_id, almacen=None, recepcion=HOY, guia=""):
    """Pasa a en proceso si hace falta (RF-COM-30) y finaliza."""
    if Compra.objects.get(pk=compra_id).estado == "CREADA":
        caso_de_compra(uc.PasarAEnProceso).ejecutar(b["actor"], compra_id)
    caso = caso_de_compra(uc.FinalizarCompra)
    caso.ejecutar(b["actor"], compra_id, almacen or b["principal"], recepcion, guia, HOY)


def stock(producto_id):
    return sum((s.cantidad for s in Stock.objects.filter(producto_id=producto_id)), D("0"))


def test_crear_y_editar_no_mueven_stock_y_numeran(base):
    """RF-COM-04 y 25: Creada con su número y totales; editar recalcula, sin movimientos."""
    compra = crear(base)
    c = Compra.objects.get(pk=compra)
    assert (c.numero, c.estado, c.total, c.igv_pct) == (1, "CREADA", D("295.00"), D("18.00"))
    caso_de_compra(uc.EditarCompra).ejecutar(
        base["actor"], compra, datos(base, [LineaCompra(base["malta"], D("40"), D("5.00"))])
    )
    c.refresh_from_db()
    assert (c.subtotal, c.igv, c.total) == (D("200.00"), D("36.00"), D("236.00"))
    assert [x.cantidad for x in c.lineas.all()] == [D("40")]
    assert crear(base, serie="F001-000846") == compra + 1
    assert Compra.objects.get(pk=compra + 1).numero == 2
    assert not Movimiento.objects.exists()


def test_en_proceso_no_vuelve_atras(base):
    compra = crear(base)
    caso_de_compra(uc.PasarAEnProceso).ejecutar(base["actor"], compra)
    assert Compra.objects.get(pk=compra).estado == "EN_PROCESO"
    with pytest.raises(CompraInvalida, match="La compra ya está en proceso"):
        caso_de_compra(uc.PasarAEnProceso).ejecutar(base["actor"], compra)


def test_finalizar_registra_la_entrada_al_costo_y_bloquea_la_compra(base):
    """RF-COM-10, 13, 26: una entrada por línea; después no se edita ni se finaliza otra vez."""
    compra = crear(base)
    finalizar(base, compra, guia="t001-00004521")
    c = Compra.objects.get(pk=compra)
    assert (c.estado, c.fecha_recepcion, c.guia_remision) == ("FINALIZADA", HOY, "T001-00004521")
    [m] = Movimiento.objects.filter(ref_tipo="COMPRA", ref_id=compra)
    assert (m.motivo, m.cantidad, m.costo_unitario) == ("COMPRA", D("50"), D("5.000000"))
    assert CostoProducto.objects.get(producto_id=base["malta"]).costo_promedio == D("5")
    with pytest.raises(CompraInvalida, match="La compra ya está finalizada"):
        finalizar(base, compra)
    with pytest.raises(CompraInvalida, match="La compra ya está finalizada"):
        caso_de_compra(uc.EditarCompra).ejecutar(base["actor"], compra, datos(base))
    assert stock(base["malta"]) == D("50")


def test_recepcion_almacen_y_guia_al_finalizar(base):
    """RF-COM-27: el stock entra al almacén confirmado con la fecha de recepción."""
    camara = Almacen.objects.create(nombre="Cámara fría").id
    compra = crear(base, fecha=HOY + timedelta(days=5))  # la fecha de compra es referencia
    hace_3 = HOY - timedelta(days=3)
    with pytest.raises(CompraInvalida, match="La fecha de recepción no puede ser futura"):
        finalizar(base, compra, recepcion=HOY + timedelta(days=1))
    with pytest.raises(CompraInvalida, match="Guía de remisión inválida"):
        finalizar(base, compra, guia="T1-ABC")
    Almacen.objects.filter(pk=camara).update(activo=False)
    with pytest.raises(CompraInvalida, match="El almacén está desactivado"):
        finalizar(base, compra, almacen=camara)
    Almacen.objects.filter(pk=camara).update(activo=True)
    finalizar(base, compra, almacen=camara, recepcion=hace_3)
    assert Compra.objects.get(pk=compra).almacen_id == camara
    [m] = Movimiento.objects.filter(ref_id=compra)
    assert (m.almacen_id, timezone.localtime(m.fecha).date()) == (camara, hace_3)


def test_lote_con_vencimiento_sugerido_desde_la_recepcion(base):
    """RF-COM-06, 07, 19: el inventario resuelve el lote nuevo, existente u otro vencimiento."""
    Producto.objects.filter(pk=base["malta"]).update(vida_util_dias=365)
    hace_3 = HOY - timedelta(days=3)
    linea = LineaCompra(base["malta"], D("10"), D("5"), lote="M-01")
    finalizar(base, crear(base, lineas=[linea]), recepcion=hace_3)
    lote = Lote.objects.get(codigo="M-01")
    assert (lote.fecha_ingreso, lote.fecha_vencimiento) == (hace_3, hace_3 + timedelta(365))
    otro = LineaCompra(base["malta"], D("5"), D("5"), lote="M-01", vencimiento=date(2030, 1, 1))
    compra = crear(base, lineas=[otro], serie="F001-9")
    with pytest.raises(LoteConOtroVencimiento, match="El lote M-01 ya existe con vencimiento"):
        finalizar(base, compra)
    assert Compra.objects.get(pk=compra).estado == "EN_PROCESO"  # no cambia nada


@pytest.mark.parametrize("caso", ["no_se_compra", "inactivo", "servicio"])
def test_solo_bienes_activos_que_se_compran(base, caso):
    """RF-COM-05, también al finalizar si el producto cambió (RF-COM-26)."""
    compra = crear(base)
    unidad = Unidad.objects.get(abreviatura="SERV" if caso == "servicio" else "KG")
    campos = {"no_se_compra": {"se_compra": False, "se_fabrica": True}, "inactivo": {}}
    campos["servicio"] = {"tipo": "SERVICIO", "se_compra": True}
    otro = Producto.objects.create(sku="X", nombre="X", unidad=unidad, **campos[caso])
    if caso == "inactivo":
        Producto.objects.filter(pk=otro.pk).update(activo=False)
    with pytest.raises(CompraInvalida, match=uc.NO_COMPRABLE):
        crear(base, lineas=[LineaCompra(otro.id, D("1"), D("1"))], serie="F001-2")
    Producto.objects.filter(pk=base["malta"]).update(se_compra=False, se_fabrica=True)
    with pytest.raises(CompraInvalida, match=uc.NO_COMPRABLE):
        finalizar(base, compra)


def test_proveedor_desactivado_y_documento_duplicado(base):
    """RF-COM-11 y 23."""
    compra = crear(base)
    with pytest.raises(CompraInvalida, match="La factura F001-000845 de Maltería del Sur ya"):
        crear(base)
    crear(base, doc="SIN_DOCUMENTO", serie="")
    crear(base, doc="SIN_DOCUMENTO", serie="")
    Compra.objects.filter(pk=compra).update(
        estado="ANULADA", anulada_en=timezone.now(), motivo_anulacion="x"
    )
    crear(base)  # una anulada no cuenta
    Proveedor.objects.filter(pk=base["proveedor"]).update(activo=False)
    with pytest.raises(CompraInvalida, match="El proveedor está desactivado"):
        crear(base, serie="F001-2")


def test_compra_sin_lineas_y_de_otra_empresa(base, crear_empresa):
    with pytest.raises(CompraInvalida, match="La compra debe tener al menos una línea"):
        caso_de_compra(uc.CrearCompra).ejecutar(base["actor"], datos(base, lineas=[]))
    with pytest.raises(NoEncontrado):
        caso_de_compra(uc.PasarAEnProceso).ejecutar(base["actor"], 999999)


def test_tiene_compras_cuenta_las_no_anuladas(base):
    """RF-COM-24: el puerto de 0002d ve las compras reales."""
    assert not puertos.compras.tiene_compras(base["proveedor"])
    compra = crear(base)
    assert puertos.compras.tiene_compras(base["proveedor"])
    Compra.objects.filter(pk=compra).update(
        estado="ANULADA", anulada_en=timezone.now(), motivo_anulacion="x"
    )
    assert not puertos.compras.tiene_compras(base["proveedor"])


def test_una_compra_creada_no_se_finaliza(base):
    """RF-COM-30: Creada ▸ En proceso ▸ Finalizada, sin saltos."""
    compra = crear(base)
    caso = caso_de_compra(uc.FinalizarCompra)
    with pytest.raises(CompraInvalida, match="Pasa la compra a en proceso antes de finalizarla"):
        caso.ejecutar(base["actor"], compra, base["principal"], HOY, "", HOY)
    assert not Movimiento.objects.exists()
