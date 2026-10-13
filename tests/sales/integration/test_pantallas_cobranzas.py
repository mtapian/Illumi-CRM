"""0006b, T8: cobranzas asociadas al pedido, pagos y métodos de pago (RF-VEN-53 a 60)."""

from datetime import timedelta
from decimal import Decimal as D

import pytest
from django.utils import timezone

from inventory.infrastructure.models import Almacen
from sales.infrastructure.contenedor import sembrar_metodos_pago
from sales.infrastructure.models import Cliente, Cobranza, Cuota, MetodoPago, Pago, Pedido
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol
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


def vencida(v):
    """Una cobranza de "Bar El Lúpulo" con su única cuota vencida ayer."""
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


def test_solo_vencidas(web):
    """RF-VEN-53: cuotas vencidas − pagos > 0."""
    client, v = web
    vencida(v)
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


def test_vendedor_no_ve_anular_ni_metodos(web, client):
    """RF-VEN-61 y 64: el rol Ventas registra pagos, pero no ve "Anular" ni gestiona métodos."""
    _, v = web
    url = f"/ventas/cobranzas/{v['cobranza']}/"
    hoy = timezone.localdate().isoformat()
    pago = {"accion": "pagar", "metodo": v["metodo"]["Efectivo"], "fecha": hoy, "monto": "10"}
    vendedor = Usuario.objects.create_user("v@andina.pe", "x", empresa_id=v["actor"].empresa_id)
    client.force_login(asignar_rol(vendedor, "Ventas"), BACKEND)
    assert client.post(url, pago).status_code == 302
    ficha = client.get(url).content.decode()
    assert "Registrar pago" in ficha and "anularPago(" not in ficha
    metodos = client.get("/ventas/metodos-pago/").content.decode()
    assert "Efectivo" in metodos and "Nuevo método de pago" not in metodos
    assert "/ventas/metodos-pago/" not in client.get("/dashboard/").content.decode()  # menú


def test_aviso_de_cobranzas_vencidas(web, client):
    """RF-VEN-62: en el inicio, con el filtro "solo vencidas"; solo con `ventas.cobranza.ver`."""
    navegador, v = web
    assert "Ninguna cobranza vencida" in navegador.get("/dashboard/").content.decode()
    vencida(v)
    inicio = navegador.get("/dashboard/").content.decode()
    assert "1 cobranza vencida" in inicio and "/ventas/cobranzas/?vencidas=1" in inicio
    planta = Usuario.objects.create_user("p@andina.pe", "x", empresa_id=v["actor"].empresa_id)
    client.force_login(asignar_rol(planta, "Producción"), BACKEND)
    assert "cobranza" not in client.get("/dashboard/").content.decode().lower()


def test_grilla_de_pedidos_con_cobranza(web):
    """RF-VEN-67 y 68: columnas, cobranza en Lista y Kanban, filtro por cobranza y orden por
    creación descendente."""
    client, v = web

    def fila(vista, numero, **filtro):
        pagina = client.get("/ventas/pedidos/", {"vista": vista, **filtro}).content.decode()
        return pagina.split(f'data-pedido="{numero}"', 1)[1].split("</tr>", 1)[0][:900]

    lista = client.get("/ventas/pedidos/").content.decode()
    columnas = ["Pedido", "Fecha y hora", "Cliente", "Comprobante", "Total", "Estado", "Cobranza"]
    cabecera = lista.split("<thead>", 1)[1].split("</thead>", 1)[0]
    assert [c for c in columnas if "<th" in cabecera and c in cabecera] == columnas
    assert "Indicadores" not in cabecera
    for vista in ("lista", "kanban"):
        assert "Por cobrar" in fila(vista, "P-000001")
    assert "Factura" in fila("lista", "P-000001")
    hoy = timezone.localdate().isoformat()
    pago = {"accion": "pagar", "metodo": v["metodo"]["Yape"], "fecha": hoy}
    client.post(f"/ventas/cobranzas/{v['cobranza']}/", pago | {"monto": "100.00"})
    assert "Cobro parcial" in fila("lista", "P-000001")
    client.post(f"/ventas/cobranzas/{v['cobranza']}/", pago | {"monto": "188.00"})
    assert "Pagado" in fila("lista", "P-000001")
    vencida(v)
    assert "Cobro vencido" in fila("lista", "P-000099")
    lista = client.get("/ventas/pedidos/").content.decode()
    assert lista.index('data-pedido="P-000099"') < lista.index('data-pedido="P-000001"')
    solo = client.get("/ventas/pedidos/", {"cobranza": "Cobro vencido"}).content.decode()
    assert 'data-pedido="P-000099"' in solo and 'data-pedido="P-000001"' not in solo


def test_cobranzas_con_fecha_y_hora_y_lo_nuevo_primero(web):
    """RF-VEN-69: fecha y hora de creación en el listado y la ficha; orden descendente."""
    client, v = web
    c = Cobranza.objects.get(pk=v["cobranza"])
    cuando = timezone.localtime(c.creado_en).strftime("%Y-%m-%d %H:%M")
    assert cuando in client.get("/ventas/cobranzas/").content.decode()
    assert cuando in client.get(f"/ventas/cobranzas/{c.id}/").content.decode()
    vencida(v)  # COB-000099, creada después
    listado = client.get("/ventas/cobranzas/").content.decode()
    assert listado.index('data-cobranza="COB-000099"') < listado.index('data-cobranza="COB-000001"')
