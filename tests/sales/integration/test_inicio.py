"""0008c, T4: inicio con tarjetas y barra de avisos (RF-FIN-14, 17)."""

import re
from datetime import timedelta

import pytest
from django.utils import timezone

from sales.infrastructure.models import Cliente, Cobranza, Cuota, Pedido
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol
from tests.sales.usecases.test_facturacion import aprobado, facturar, preparar

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, empresa_ventas):
    empresa, actor = empresa_ventas
    v = preparar(empresa, actor, timezone.localdate())
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    return client, v


def tarjetas(html) -> dict:
    return dict(re.findall(r'data-tarjeta="([^"]+)".*?<strong[^>]*>([^<]+)</strong>', html, re.S))


def test_tarjetas_con_sus_valores(web):
    """RF-FIN-14: ventas de hoy y del mes con impuestos; productos y clientes activos."""
    client, v = web
    from tests.sales.usecases import test_facturacion as tf

    original, tf.HOY = tf.HOY, timezone.localdate()
    try:
        facturar(v, aprobado(v, ("TER-IPA-330", "24", "12")))
    finally:
        tf.HOY = original
    html = client.get("/dashboard/").content.decode()
    assert tarjetas(html) == {
        "Ventas de hoy": "S/ 288.00",
        "Ventas del mes": "S/ 288.00",
        "Productos activos": "3",
        "Clientes activos": "3",
    }
    assert timezone.localdate().strftime("%Y") in html  # la fecha de hoy en las migas


def test_cada_tarjeta_con_su_permiso(web, client):
    """RF-FIN-14: Producción ve productos, no ventas ni clientes."""
    _, v = web
    planta = Usuario.objects.create_user("p@andina.pe", "x", empresa_id=v["actor"].empresa_id)
    client.force_login(asignar_rol(planta, "Producción"), BACKEND)
    assert set(tarjetas(client.get("/dashboard/").content.decode())) == {"Productos activos"}


def test_barra_de_avisos_solo_con_algo_pendiente(web):
    """RF-FIN-17: sin avisos no hay barra; con una cobranza vencida, su línea y su enlace."""
    client, v = web
    assert 'class="barra-avisos"' not in client.get("/dashboard/").content.decode()
    ayer = timezone.localdate() - timedelta(days=1)
    bar = Cliente.objects.get(pk=v["clientes"]["bar"])
    from inventory.infrastructure.models import Almacen

    pedido = Pedido.objects.create(
        numero=99, cliente=bar, fecha_entrega=ayer, estado="FACTURADO", comprobante="FACTURA",
        forma_pago="CREDITO", fecha_emision=ayer - timedelta(days=30), total=100,
        almacen=Almacen.objects.get(nombre="Principal"),
    )  # fmt: skip
    c = Cobranza.objects.create(
        numero=99, pedido=pedido, cliente=bar, emision=pedido.fecha_emision, total=100
    )
    Cuota.objects.create(cobranza=c, numero=1, monto=100, vencimiento=ayer)
    html = client.get("/dashboard/").content.decode()
    barra = html.split('class="barra-avisos"', 1)[1].split("</section>", 1)[0]
    assert "1 cobranza vencida" in barra and "/ventas/cobranzas/?vencidas=1" in barra
    assert "quiebre" not in barra  # lo que no tiene nada no aparece


def _facturar_hoy(v, *lineas):
    from tests.sales.usecases import test_facturacion as tf

    original, tf.HOY = tf.HOY, timezone.localdate()
    try:
        id_ = aprobado(v, *lineas)
        facturar(v, id_)
        return id_
    finally:
        tf.HOY = original


def test_graficos_y_tablas(web):
    """RF-FIN-18 a 23: los cuatro gráficos y las dos tablas, con sus valores."""
    client, v = web
    id_ = _facturar_hoy(v, ("TER-IPA-330", "24", "12"))
    html = client.get("/dashboard/").content.decode()
    for titulo in (
        "Ventas de los últimos 14 días",
        "Ventas por mes",
        "Cobrado por método de pago",
        "Ventas por categoría",
        "Productos más vendidos",
        "Últimas ventas",
    ):
        assert f'aria-label="{titulo}"' in html, titulo
    hoy = timezone.localdate().strftime("%d/%m")
    assert f'data-etiqueta="{hoy}" data-valor="288.00"' in html
    assert 'data-etiqueta="Sin categoría" data-valor="288.00"' in html
    vendidos = html.split('aria-label="Productos más vendidos"', 1)[1].split("</section>", 1)[0]
    assert "TER-IPA-330" in vendidos and "24" in vendidos and "S/ 288.00" in vendidos
    ultimas = html.split('aria-label="Últimas ventas"', 1)[1].split("</section>", 1)[0]
    assert f'href="/ventas/pedidos/{id_}/"' in ultimas and "P-000001" in ultimas
    assert "Aún no hay ventas" in html  # sin cobros todavía, la dona no falla (RF-FIN-24)


def test_paneles_con_permiso(web, client):
    """RF-FIN-14: Producción no ve los paneles de ventas."""
    _, v = web
    planta = Usuario.objects.create_user("p@andina.pe", "x", empresa_id=v["actor"].empresa_id)
    client.force_login(asignar_rol(planta, "Producción"), BACKEND)
    assert "Ventas por mes" not in client.get("/dashboard/").content.decode()


def test_rendimiento_con_10000_ventas(web):
    """RNF-FIN-04: el inicio responde en menos de 800 ms (p95) con 10 000 ventas."""
    import time

    from inventory.infrastructure.models import Almacen
    from sales.infrastructure.models import PedidoLinea

    client, v = web
    hoy, cliente = timezone.localdate(), Cliente.objects.get(pk=v["clientes"]["bar"])
    pedidos = Pedido.objects.bulk_create(
        Pedido(empresa_id=v["actor"].empresa_id, numero=1000 + i, cliente=cliente,
               fecha_entrega=hoy, total=12)
        for i in range(10_000)
    )  # fmt: skip
    PedidoLinea.objects.bulk_create(
        PedidoLinea(empresa_id=v["actor"].empresa_id, pedido=p, producto_id=v["ids"]["TER-IPA-330"],
                    cantidad=1, precio=12, subtotal=12, valor="10.17", isc=0, igv="1.83", costo=4)
        for p in pedidos
    )  # fmt: skip
    Pedido.objects.filter(numero__gte=1000).update(
        estado="FACTURADO", comprobante="FACTURA", forma_pago="CONTADO", fecha_emision=hoy,
        almacen=Almacen.objects.get(nombre="Principal"), facturado_en=timezone.now(),
    )  # fmt: skip
    tiempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        assert client.get("/dashboard/").status_code == 200
        tiempos.append(time.perf_counter() - inicio)
    assert sorted(tiempos)[18] < 0.8
