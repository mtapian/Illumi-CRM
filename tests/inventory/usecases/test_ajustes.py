"""0003b, T5 a T8: registrar y anular ajustes (RF-INV-08 a 13, 27 a 29)."""

from datetime import date
from decimal import Decimal as D

import pytest

from inventory.application import ajustes as uc
from inventory.application.ajustes import LineaAjuste
from inventory.domain.errores import (
    AjusteInvalido,
    AnulacionConConsumoPosterior,
    CostoRequerido,
    StockInsuficiente,
)
from inventory.infrastructure.contenedor import caso_de_ajuste
from inventory.infrastructure.models import (
    Ajuste,
    Almacen,
    CostoProducto,
    Lote,
    Movimiento,
    Stock,
)
from tenancy.infrastructure.contenedor import actor_de

pytestmark = pytest.mark.django_db
HOY = date(2026, 11, 1)


@pytest.fixture
def actor(inv):
    return actor_de(inv["admin"], date.today())


def registrar(actor, inv, tipo, lineas, motivo="Prueba", almacen=None, destino=None):
    caso = caso_de_ajuste(uc.RegistrarAjuste)
    return caso.ejecutar(actor, tipo, almacen or inv["principal"], motivo, lineas, destino, HOY)


def costo(inv, producto="malta"):
    c = CostoProducto.objects.get(producto_id=inv[producto])
    return c.cantidad_total, c.valor_total, c.costo_promedio


def test_saldo_inicial_merma_y_correccion(inv, actor):
    """T5, RF-INV-08 a 10: numeración, lote opcional y costo por tipo."""
    a1 = registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("100"), costo=D("4"))])
    lote = LineaAjuste(inv["ipa"], D("60"), costo=D("4.1"), lote="IPA-0009")
    registrar(actor, inv, "SALDO_INICIAL", [lote])
    assert Lote.objects.get(codigo="IPA-0009").fecha_vencimiento == date(2027, 3, 1)
    registrar(actor, inv, "MERMA", [LineaAjuste(inv["malta"], D("10"))], "Saco roto")
    entrada = LineaAjuste(inv["malta"], D("10"), sentido="ENTRADA")  # al promedio vigente
    registrar(actor, inv, "CORRECCION", [entrada], "Hallazgo")
    assert costo(inv) == (D("100.0000"), D("400.00"), D("4.000000"))
    assert list(Ajuste.objects.order_by("numero").values_list("numero", flat=True)) == [1, 2, 3, 4]
    assert Movimiento.objects.filter(ref_tipo="AJUSTE", ref_id=a1).count() == 1


def test_validaciones_al_registrar(inv, actor):
    """RF-INV-08, 09, 27."""
    with pytest.raises(AjusteInvalido, match="El motivo es obligatorio"):
        registrar(actor, inv, "MERMA", [LineaAjuste(inv["malta"], D("1"))], " ")
    with pytest.raises(AjusteInvalido, match="costo unitario mayor a 0"):
        registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("20"))])
    with pytest.raises(CostoRequerido):
        registrar(actor, inv, "CORRECCION", [LineaAjuste(inv["malta"], D("1"), sentido="ENTRADA")])
    registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("1"), costo=D("4"))])
    with pytest.raises(AjusteInvalido, match="solo sirve para la apertura"):
        registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("1"), costo=D("4"))])
    with pytest.raises(AjusteInvalido, match="Indica si la corrección es entrada o salida"):
        registrar(actor, inv, "CORRECCION", [LineaAjuste(inv["malta"], D("1"))])
    with pytest.raises(AjusteInvalido, match="al menos una línea"):
        registrar(actor, inv, "MERMA", [])
    assert Ajuste.objects.count() == 1  # los rechazados no dejan nada


def test_conteo_calcula_la_diferencia(inv, actor):
    """T6, RF-INV-11: igual no mueve stock; menos sale al promedio; lote vencido permitido."""
    registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("1500"), costo=D("0.12"))])
    igual = registrar(actor, inv, "CONTEO", [LineaAjuste(inv["malta"], D("1500"))])
    assert not Movimiento.objects.filter(ref_tipo="AJUSTE", ref_id=igual).exists()
    assert Ajuste.objects.get(pk=igual).lineas.get().cantidad_sistema == D("1500")
    menos = registrar(actor, inv, "CONTEO", [LineaAjuste(inv["malta"], D("1420"))])
    m = Movimiento.objects.get(ref_tipo="AJUSTE", ref_id=menos)
    assert (m.tipo, m.motivo, m.cantidad, m.costo_unitario) == (
        "SALIDA",
        "CONTEO",
        D("80.0000"),
        D("0.120000"),
    )
    lote = LineaAjuste(inv["ipa"], D("10"), costo=D("4"), lote="V", vencimiento=date(2026, 10, 1))
    registrar(actor, inv, "SALDO_INICIAL", [lote])
    registrar(actor, inv, "CONTEO", [LineaAjuste(inv["ipa"], D("7"), lote="V")])
    assert Stock.objects.get(lote__codigo="V").cantidad == D("7.0000")


def test_transferencia_no_cambia_el_costo(inv, actor):
    """T7, RF-INV-12: también cuando vacía el origen y el promedio no es exacto."""
    taproom = Almacen.objects.create(nombre="Taproom").id
    registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("3"), costo=D("0.333333"))])
    antes = costo(inv)
    registrar(actor, inv, "TRANSFERENCIA", [LineaAjuste(inv["malta"], D("3"))], destino=taproom)
    assert costo(inv) == antes
    assert Stock.objects.get(almacen_id=taproom).cantidad == D("3.0000")
    assert Stock.objects.get(almacen_id=inv["principal"]).cantidad == 0
    salida, entrada = Movimiento.objects.filter(motivo="TRANSFERENCIA").order_by("id")
    assert (salida.tipo, entrada.tipo, salida.costo_total) == (
        "SALIDA",
        "ENTRADA",
        entrada.costo_total,
    )
    with pytest.raises(StockInsuficiente):
        registrar(actor, inv, "TRANSFERENCIA", [LineaAjuste(inv["malta"], D("1"))], destino=taproom)


def test_anular_merma_conteo_y_transferencia(inv, actor):
    """T8, RF-INV-13: inversos al costo original; transferencia sin cambiar el costo."""
    anular = caso_de_ajuste(uc.AnularAjuste)
    registrar(actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("100"), costo=D("4"))])
    merma = registrar(actor, inv, "MERMA", [LineaAjuste(inv["malta"], D("20"))])
    anular.ejecutar(actor, merma, "Saco recuperado")
    inverso = Movimiento.objects.get(revierte__ref_id=merma)
    assert (inverso.tipo, inverso.motivo, inverso.cantidad) == (
        "ENTRADA",
        "ANULACION",
        D("20.0000"),
    )
    a = Ajuste.objects.get(pk=merma)
    assert (a.estado, a.motivo_anulacion, a.anulado_por_id) == (
        "ANULADO",
        "Saco recuperado",
        inv["admin"].id,
    )
    with pytest.raises(AjusteInvalido, match="El ajuste ya está anulado"):
        anular.ejecutar(actor, merma, "Otra vez")
    taproom = Almacen.objects.create(nombre="Taproom").id
    t = registrar(
        actor, inv, "TRANSFERENCIA", [LineaAjuste(inv["malta"], D("30"))], destino=taproom
    )
    antes = costo(inv)
    anular.ejecutar(actor, t, "Error de almacén")
    assert costo(inv) == antes
    assert Stock.objects.get(almacen_id=taproom).cantidad == 0
    igual = registrar(actor, inv, "CONTEO", [LineaAjuste(inv["malta"], D("100"))])
    anular.ejecutar(actor, igual, "Sin efecto")  # sin movimientos: solo cambia el estado
    with pytest.raises(AjusteInvalido, match="El motivo es obligatorio"):
        anular.ejecutar(
            actor, registrar(actor, inv, "MERMA", [LineaAjuste(inv["malta"], D("1"))]), ""
        )


def test_no_se_anula_un_saldo_inicial_consumido(inv, actor):
    """RF-INV-13 con RF-INV-21 (Q12 = A)."""
    saldo = registrar(
        actor, inv, "SALDO_INICIAL", [LineaAjuste(inv["malta"], D("10"), costo=D("4"))]
    )
    registrar(actor, inv, "MERMA", [LineaAjuste(inv["malta"], D("1"))])
    with pytest.raises(AnulacionConConsumoPosterior):
        caso_de_ajuste(uc.AnularAjuste).ejecutar(actor, saldo, "Error")
    assert Ajuste.objects.get(pk=saldo).estado == "REGISTRADO"
