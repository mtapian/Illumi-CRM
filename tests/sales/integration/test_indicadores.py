"""0008c, T8: tarjetas por estado sobre las grillas de pedidos y cobranzas (RF-FIN-26)."""

import re

import pytest
from django.utils import timezone

from tenancy.infrastructure.models import Usuario
from tests.sales.usecases import test_facturacion as tf
from tests.sales.usecases.test_facturacion import aprobado, facturar, preparar

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, empresa_ventas, monkeypatch):
    empresa, actor = empresa_ventas
    hoy = timezone.localdate()
    monkeypatch.setattr(tf, "HOY", hoy)
    v = preparar(empresa, actor, hoy)
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    from sales.application import pedidos as up
    from sales.infrastructure.contenedor import caso_de_pedido

    datos = up.DatosPedido(v["clientes"]["bar"], hoy, "", ())
    caso_de_pedido(up.CrearPedido).ejecutar(actor, datos)  # Creado, sin líneas
    aprobado(v, ("TER-IPA-330", "1", "12"))  # Aprobado
    facturar(v, aprobado(v, ("TER-IPA-330", "24", "12")))  # Facturado, cobranza Pendiente
    facturar(v, aprobado(v, ("TER-IPA-330", "2", "12"), cliente="ana"))  # otro cliente
    return client, v


def tarjetas(html) -> dict:
    return {
        t: int(n)
        for t, n in re.findall(
            r'data-indicador="([^"]+)"[^>]*>.*?<strong>(\d+)</strong>', html, re.S
        )
    }


def test_pedidos_por_estado_con_los_filtros(web):
    client, v = web
    html = client.get("/ventas/pedidos/").content.decode()
    assert tarjetas(html) == {"Creados": 1, "Aprobados": 1, "Facturados": 2, "Entregados": 0}
    bar = client.get("/ventas/pedidos/", {"cliente": v["clientes"]["bar"], "estado": "CREADO"})
    html = bar.content.decode()
    assert tarjetas(html) == {"Creados": 1, "Aprobados": 1, "Facturados": 1, "Entregados": 0}
    assert f"cliente={v['clientes']['bar']}&amp;estado=FACTURADO" in html  # la tarjeta filtra


def test_cobranzas_por_estado_con_su_saldo(web):
    client, _ = web
    html = client.get("/ventas/cobranzas/").content.decode()
    assert tarjetas(html) == {"Pendientes": 2, "Parciales": 0, "Pagadas": 0, "Vencidas": 0}
    pendientes = html.split('data-indicador="Pendientes"', 1)[1].split("</a>", 1)[0]
    assert "S/ 312.00" in pendientes  # 288.00 + 24.00 de saldo
    assert "vencidas=1" in html
