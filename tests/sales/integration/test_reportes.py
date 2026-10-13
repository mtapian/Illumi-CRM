"""0008c, T3: consultas agregadas del inicio (RF-FIN-14, 18 a 23)."""

from datetime import date, datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo

import pytest

from catalog.infrastructure.models import Categoria, Producto
from sales.application import cobranzas as ucob
from sales.infrastructure import reportes
from sales.infrastructure.contenedor import caso_de_cobranza, sembrar_metodos_pago
from sales.infrastructure.models import Cobranza, MetodoPago, Pedido
from tests.sales.usecases.test_facturacion import HOY, aprobado, facturar, preparar

pytestmark = pytest.mark.django_db
LIMA = ZoneInfo("America/Lima")


@pytest.fixture
def v(empresa_ventas):
    """Ventas: P-1 (24 IPA) el 2026-11-20, P-2 (5 IPA + 1 barril) el 2026-12-01, P-3 cancelado.
    Pagos de P-2: Efectivo 50 y Yape 20 (anulado)."""
    empresa, actor = empresa_ventas
    v = preparar(empresa, actor, date(2026, 11, 1))
    sembrar_metodos_pago(empresa.id, actor.usuario_id, HOY)
    cervezas = Categoria.objects.create(nombre="Cervezas")
    Producto.objects.filter(sku="TER-IPA-330").update(categoria=cervezas)

    def venta(dia, *lineas):
        id_ = aprobado(v, *lineas)
        facturar_el(v, id_, dia)
        return id_

    v["p1"] = venta(date(2026, 11, 20), ("TER-IPA-330", "24", "12"))
    v["p2"] = venta(HOY, ("TER-IPA-330", "5", "12"), ("SRV-FLETE", "1", "20"))
    p3 = aprobado(v, ("TER-IPA-330", "1", "12"))
    Pedido.objects.filter(pk=p3).update(estado="CANCELADO", motivo_cancelacion="x")
    metodos = {m.nombre: m.id for m in MetodoPago.objects.all()}
    cobranza = Cobranza.objects.get(pedido_id=v["p2"]).id
    pagar = caso_de_cobranza(ucob.RegistrarPago)
    pagar.ejecutar(actor, cobranza, ucob.DatosPago(metodos["Efectivo"], D("50"), HOY), HOY)
    yape = pagar.ejecutar(actor, cobranza, ucob.DatosPago(metodos["Yape"], D("20"), HOY), HOY)
    caso_de_cobranza(ucob.AnularPago).ejecutar(actor, yape, "Error")
    return v


def facturar_el(v, pedido_id, dia):
    """Factura con la fecha de emisión `dia` (la vista de inicio agrupa por ella)."""
    from tests.sales.usecases import test_facturacion as tf

    original = tf.HOY
    tf.HOY = dia
    try:
        facturar(v, pedido_id)
    finally:
        tf.HOY = original
    hora = datetime(dia.year, dia.month, dia.day, 23, 30, tzinfo=LIMA)  # cae en ese día
    Pedido.objects.filter(pk=pedido_id).update(facturado_en=hora)


def test_ventas_de_un_dia_y_de_un_mes(v):
    """RF-FIN-14: con impuestos, por fecha de emisión; los cancelados no cuentan."""
    assert reportes.ventas_entre(HOY, HOY) == D("80.00")
    assert reportes.ventas_entre(date(2026, 11, 1), date(2026, 11, 30)) == D("288.00")
    assert reportes.ventas_entre(date(2026, 1, 1), date(2026, 1, 31)) == D("0")


def test_ventas_por_dia_y_por_mes(v):
    """RF-FIN-18 y 19: días y meses sin ventas en 0."""
    dias = reportes.ventas_por_dia(HOY, 14)
    assert (
        len(dias) == 14 and dias[0][0] == HOY - timedelta(days=13) and dias[-1] == (HOY, D("80.00"))
    )
    assert dict(dias)[date(2026, 11, 20)] == D("288.00")
    meses = reportes.ventas_por_mes(2026)
    assert len(meses) == 12 and meses[10] == (11, D("288.00")) and meses[11] == (12, D("80.00"))


def test_cobrado_por_metodo(v):
    """RF-FIN-20: pagos vigentes por su fecha; el anulado no cuenta."""
    assert reportes.cobrado_por_metodo(date(2026, 12, 1), date(2026, 12, 31)) == [
        ("Efectivo", D("50.00"))
    ]


def test_ventas_por_categoria_y_mas_vendidos(v):
    """RF-FIN-21 y 22."""
    mes = (date(2026, 12, 1), date(2026, 12, 31))
    assert reportes.ventas_por_categoria(*mes) == [
        ("Cervezas", D("60.00")),
        ("Sin categoría", D("20.00")),
    ]
    vendidos = reportes.mas_vendidos(date(2026, 11, 1), date(2026, 12, 31))
    assert vendidos[0] == ("TER-IPA-330", "TER-IPA-330", D("29"), D("348.00"))
    assert vendidos[1][0] == "SRV-FLETE"


def test_ultimas_ventas(v):
    """RF-FIN-23: las más recientes por fecha y hora de facturación."""
    assert [p.id for p in reportes.ultimas_ventas(6)] == [v["p2"], v["p1"]]
