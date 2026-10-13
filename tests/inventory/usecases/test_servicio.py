"""0003a, T11, T12 y T14: el servicio de inventario registra entradas, salidas y
reversiones con su costo y saldo (RF-INV-17 a 26)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.utils import timezone

from inventory.application.servicio import Consumo, Linea
from inventory.domain.errores import (
    AnulacionConConsumoPosterior,
    LoteConOtroVencimiento,
    LoteVencido,
    ServicioSinStock,
    StockInsuficiente,
)
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import CostoProducto, Lote, Movimiento, Stock

pytestmark = pytest.mark.django_db
HOY = date(2026, 11, 1)


def entra(inv, producto, cant, costo, ref_id=1, motivo="COMPRA", **kw):
    linea = Linea(inv[producto], inv["principal"], D(cant), D(costo), **kw)
    return inventario().registrar_entrada(motivo, "COMPRA", ref_id, [linea], inv["admin"].id, HOY)


def sale(inv, producto, cant, motivo="VENTA", **kw):
    linea = Linea(inv[producto], inv["principal"], D(cant), **kw)
    return inventario().registrar_salida(motivo, "VENTA", 9, [linea], inv["admin"].id, HOY)


def costo(inv, producto):
    c = CostoProducto.objects.get(producto_id=inv[producto])
    return c.cantidad_total, c.valor_total, c.costo_promedio


def test_cada_entrada_genera_un_movimiento_con_su_saldo(inv):
    """T11, RF-INV-17 y RF-INV-18."""
    entra(inv, "malta", "100", "4")
    entra(inv, "malta", "50", "5", ref_id=2)
    m = Movimiento.objects.order_by("id").last()
    assert (m.tipo, m.motivo, m.cantidad, m.costo_unitario, m.costo_total) == (
        "ENTRADA",
        "COMPRA",
        D("50.0000"),
        D("5.000000"),
        D("250.00"),
    )
    assert (m.saldo_cantidad, m.saldo_promedio) == (D("150.0000"), D("4.333333"))
    assert costo(inv, "malta") == (D("150.0000"), D("650.00"), D("4.333333"))
    assert Stock.objects.get(producto_id=inv["malta"]).cantidad == D("150.0000")
    assert Movimiento.objects.count() == 2


def test_entrada_con_lote_nuevo_sugiere_vencimiento_y_rechaza_otro(inv):
    """T11, RF-INV-26."""
    entra(inv, "ipa", "24", "4", lote="IPA-0020")
    assert Lote.objects.get(codigo="IPA-0020").fecha_vencimiento == date(2027, 3, 1)
    entra(inv, "ipa", "12", "4", lote="IPA-0020")  # mismo lote, sin indicar vencimiento
    assert Stock.objects.get(lote__codigo="IPA-0020").cantidad == D("36.0000")
    with pytest.raises(LoteConOtroVencimiento, match="ya existe con vencimiento 2027-03-01"):
        entra(inv, "ipa", "1", "4", lote="IPA-0020", vencimiento=date(2027, 4, 1))


def test_servicio_no_lleva_stock(inv):
    """RF-INV-25."""
    with pytest.raises(ServicioSinStock):
        entra(inv, "tour", "1", "0")
    assert not Movimiento.objects.exists()


def test_salida_sin_lote_no_deja_negativo_y_no_registra_nada(inv):
    """T12, RF-INV-19."""
    entra(inv, "malta", "5", "4")
    msg = "Stock insuficiente de INS-MALTA en Principal: disponible 5.0000, requerido 6.0000"
    with pytest.raises(StockInsuficiente, match=msg):
        sale(inv, "malta", "6", motivo="MERMA")
    assert Movimiento.objects.count() == 1


def test_salida_al_promedio_y_la_que_vacia(inv):
    """T12, RF-INV-24."""
    entra(inv, "malta", "3", "0.333333")  # 3 × 0.333333 = 1.00
    [m1] = sale(inv, "malta", "1")
    [m2] = sale(inv, "malta", "2")
    assert [x.costo_total for x in Movimiento.objects.filter(pk__in=[m1, m2])] == [
        D("0.33"),
        D("0.67"),
    ]
    assert costo(inv, "malta") == (D("0.0000"), D("0.00"), D("0.333333"))


def test_salida_por_fefo_y_lote_vencido_solo_por_merma(inv):
    """T12, RF-INV-22 y RF-INV-23."""
    entra(inv, "ipa", "10", "4", lote="IPA-0012", vencimiento=date(2026, 10, 30))
    entra(inv, "ipa", "48", "4", lote="IPA-0015", vencimiento=date(2026, 12, 15))
    entra(inv, "ipa", "120", "4", lote="IPA-0018", vencimiento=date(2027, 2, 20))
    sale(inv, "ipa", "60")
    salidas = Movimiento.objects.filter(tipo="SALIDA").order_by("id")
    assert [(m.lote.codigo, m.cantidad) for m in salidas] == [
        ("IPA-0015", D("48.0000")),
        ("IPA-0018", D("12.0000")),
    ]
    with pytest.raises(StockInsuficiente, match="108 UND sin vencer"):
        sale(inv, "ipa", "200")
    with pytest.raises(LoteVencido):
        sale(inv, "ipa", "10", motivo="CORRECCION", lote="IPA-0012")
    sale(inv, "ipa", "10", motivo="MERMA", lote="IPA-0012")
    assert Stock.objects.get(lote__codigo="IPA-0012").cantidad == 0


def test_revertir_una_entrada_al_costo_original(inv):
    """T14, RF-INV-20: el promedio vuelve a 4.000000; no se revierte dos veces."""
    entra(inv, "malta", "100", "4", ref_id=1)
    entra(inv, "malta", "50", "5", ref_id=2)
    [inverso] = inventario().revertir("COMPRA", 2, inv["admin"].id)
    m = Movimiento.objects.get(pk=inverso)
    assert (m.tipo, m.costo_unitario, m.costo_total, m.revierte.ref_id) == (
        "SALIDA",
        D("5.000000"),
        D("250.00"),
        2,
    )
    assert costo(inv, "malta") == (D("100.0000"), D("400.00"), D("4.000000"))
    assert inventario().revertir("COMPRA", 2, inv["admin"].id) == []  # ya revertida


def test_entrada_consumida_no_se_revierte(inv):
    """T14, RF-INV-21 (Q12 = A)."""
    entra(inv, "malta", "100", "4", ref_id=1)
    sale(inv, "malta", "1")
    with pytest.raises(AnulacionConConsumoPosterior, match="ajuste CORRECCION"):
        inventario().revertir("COMPRA", 1, inv["admin"].id)


def test_revertir_una_salida_devuelve_el_stock_a_su_lote(inv):
    entra(inv, "ipa", "10", "4", lote="IPA-0015", vencimiento=date(2026, 12, 15))
    sale(inv, "ipa", "4")
    inventario().revertir("VENTA", 9, inv["admin"].id)
    assert Stock.objects.get(lote__codigo="IPA-0015").cantidad == D("10.0000")
    assert costo(inv, "ipa") == (D("10.0000"), D("40.00"), D("4.000000"))


def test_existencias_en_orden_consumido_y_fecha_de_la_salida(inv):
    """0005a, T3 (RF-PRD-09, 39, 41, 46): existencias en el orden de la estrategia, sin
    vencidos; lote, cantidad e importe de cada salida; la salida lleva la fecha de negocio."""
    entra(inv, "ipa", "10", "4", lote="IPA-0012", vencimiento=date(2026, 10, 30))
    entra(inv, "ipa", "48", "4", lote="IPA-0015", vencimiento=date(2026, 12, 15))
    entra(inv, "ipa", "120", "4", lote="IPA-0018", vencimiento=date(2027, 2, 20))
    servicio = inventario()
    orden = servicio.existencias_en_orden(inv["ipa"], inv["principal"], HOY)
    assert orden == [("IPA-0015", D("48.0000")), ("IPA-0018", D("120.0000"))]
    ids = sale(inv, "ipa", "60")
    assert servicio.consumido(ids) == [
        Consumo(inv["ipa"], "IPA-0015", D("48.0000"), D("192.00")),
        Consumo(inv["ipa"], "IPA-0018", D("12.0000"), D("48.00")),
    ]
    fechas = {timezone.localtime(m.fecha).date() for m in Movimiento.objects.filter(pk__in=ids)}
    assert fechas == {HOY}


def test_disponibles_suma_almacenes_y_excluye_vencidos(inv):
    """0006a, T7 (RF-VEN-45): stock sin vencer por producto, sumando almacenes; 0 sin stock."""
    from inventory.infrastructure.models import Almacen

    taproom = Almacen.objects.create(nombre="Taproom").id
    entra(inv, "ipa", "10", "4", lote="IPA-0012", vencimiento=date(2026, 10, 30))  # vencido
    entra(inv, "ipa", "48", "4", lote="IPA-0015", vencimiento=date(2026, 12, 15))
    linea = Linea(inv["ipa"], taproom, D("5"), D("4"))
    inventario().registrar_entrada("COMPRA", "COMPRA", 3, [linea], inv["admin"].id, HOY)
    assert inventario().disponibles([inv["ipa"], inv["malta"]], HOY) == {
        inv["ipa"]: D("53.0000"),
        inv["malta"]: D("0"),
    }
