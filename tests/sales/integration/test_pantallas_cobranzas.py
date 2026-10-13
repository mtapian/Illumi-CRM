"""0006b, T8: cobranzas asociadas al pedido, pagos y métodos de pago (RF-VEN-53 a 60)."""

from datetime import timedelta
from decimal import Decimal as D

import pytest
from django.utils import timezone

from inventory.infrastructure.models import Almacen
from sales.infrastructure.contenedor import sembrar_metodos_pago
from sales.infrastructure.models import Cliente, Cobranza, Cuota, MetodoPago, Pago, Pedido
from tenancy.infrastructure.models import Usuario
from tests.sales.usecases.test_facturacion import aprobado, preparar

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, empresa_ventas):
    empresa, actor = empresa_ventas
    hoy = timezone.localdate()
    v = preparar(empresa, actor, hoy)
    sembrar_metodos_pago(empresa.id, actor.usuario_id, hoy)
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    pedido = aprobado(v, ("TER-IPA-330", "24", "12"))
    client.post(f"/ventas/pedidos/{pedido}/", {"accion": "facturar", "almacen": v["almacen"]})
    v["pedido"], v["cobranza"] = pedido, Cobranza.objects.get(pedido_id=pedido).id
    v["metodo"] = {m.nombre: m.id for m in MetodoPago.objects.all()}
    return client, v


def test_cobranza_asociada_al_pedido(web):
    """RF-VEN-53 y 60: el listado y el pedido llevan a la cobranza, y la cobranza a su pedido."""
    client, v = web
    url = f"/ventas/cobranzas/{v['cobranza']}/"
    listado = client.get("/ventas/cobranzas/").content.decode()
    for texto in ("COB-000001", "P-000001", "Bar El Lúpulo", "288.00", url):
        assert texto in listado, texto
    assert url in client.get(f"/ventas/pedidos/{v['pedido']}/").content.decode()
    ficha = client.get(url).content.decode()
    for texto in ("COB-000001", f"/ventas/pedidos/{v['pedido']}/", "Registrar pago", "Efectivo"):
        assert texto in ficha, texto


def test_registrar_y_anular_pagos(web):
    """RF-VEN-54 a 57."""
    client, v = web
    url = f"/ventas/cobranzas/{v['cobranza']}/"
    hoy = timezone.localdate().isoformat()
    pago = {"accion": "pagar", "metodo": v["metodo"]["Transferencia"], "fecha": hoy}
    assert client.post(url, pago | {"monto": "100.00", "referencia": "op-1"}).status_code == 302
    assert Cobranza.objects.get(pk=v["cobranza"]).pagado == D("100.00")
    assert "Parcial" in client.get(url).content.decode()
    assert "Parcial" in client.get(f"/ventas/pedidos/{v['pedido']}/").content.decode()
    error = client.post(url, pago | {"monto": "300.00"}).content.decode()
    assert "El pago debe ser mayor a 0 y no superar el saldo (188.00)" in error
    x = Pago.objects.get()
    anular = {"accion": "anular", "pago": x.id, "motivo": "Monto mal digitado"}
    assert client.post(url, anular).status_code == 302
    ficha = client.get(url).content.decode()
    assert "Anulado" in ficha and "Monto mal digitado" in ficha
    assert Cobranza.objects.get(pk=v["cobranza"]).pagado == D("0.00")


def test_solo_vencidas(web):
    """RF-VEN-53: cuotas vencidas − pagos > 0."""
    client, v = web
    ayer = timezone.localdate() - timedelta(days=1)
    bar = Cliente.objects.get(pk=v["clientes"]["bar"])
    pedido = Pedido.objects.create(
        numero=99, cliente=bar, fecha_entrega=ayer, estado="FACTURADO", comprobante="FACTURA",
        forma_pago="CREDITO", fecha_emision=ayer - timedelta(days=30), total=D("100.00"),
        almacen=Almacen.objects.get(nombre="Principal"),
    )  # fmt: skip
    c = Cobranza.objects.create(
        numero=99, pedido=pedido, cliente=bar, emision=pedido.fecha_emision, total=D("100.00")
    )
    Cuota.objects.create(cobranza=c, numero=1, monto=D("100.00"), vencimiento=ayer)
    listado = client.get("/ventas/cobranzas/", {"vencidas": "1"}).content.decode()
    assert "COB-000099" in listado and "Vencida" in listado and "COB-000001" not in listado


def test_metodos_de_pago(web):
    """RF-VEN-58 y 59: listado de maestro sin eliminar."""
    client, v = web
    pagina = client.get("/ventas/metodos-pago/").content.decode()
    assert "Transferencia" in pagina and "Eliminar" not in pagina
    client.post("/ventas/metodos-pago/", {"accion": "guardar", "nombre": "Depósito BCP"})
    assert MetodoPago.objects.filter(nombre="Depósito BCP").exists()
    error = client.post("/ventas/metodos-pago/", {"accion": "guardar", "nombre": "yape"})
    assert "Ya existe un método de pago con ese nombre" in error.content.decode()
    client.post("/ventas/metodos-pago/", {"accion": "desactivar", "id": v["metodo"]["Plin"]})
    assert not MetodoPago.objects.get(nombre="Plin").activo
    ficha = client.get(f"/ventas/cobranzas/{v['cobranza']}/").content.decode()
    assert "Plin" not in ficha
