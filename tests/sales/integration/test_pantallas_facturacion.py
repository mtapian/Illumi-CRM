"""0006b, T6 y T7: facturar y entregar desde la ficha del pedido; resumen del cliente (RF-VEN-04,
17, 19, 20, 51)."""

import re

import pytest
from django.utils import timezone

from sales.infrastructure.contenedor import sembrar_metodos_pago
from sales.infrastructure.models import MetodoPago, Pedido
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol
from tests.sales.usecases.test_facturacion import aprobado, preparar

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, empresa_ventas):
    empresa, actor = empresa_ventas
    v = preparar(empresa, actor, timezone.localdate())
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    return client, v


def test_facturar_y_entregar_desde_la_ficha(web):
    client, v = web
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    url = f"/ventas/pedidos/{id_}/"
    ficha = client.get(url).content.decode()
    assert "Facturar" in ficha and "Factura" in ficha and "Crédito" in ficha
    assert "IPA-0020" in ficha  # lotes para elegir (RF-VEN-20)

    base = {"accion": "facturar", "almacen": v["almacen"]}
    credito = base | {"forma_pago": "CREDITO", "cuota_monto": "288.00", "cuota_dias": "0"}
    error = client.post(url, credito).content.decode()
    assert "El vencimiento de cada cuota debe ser posterior a la emisión" in error
    assert Pedido.objects.get(pk=id_).estado == "APROBADO"

    lote = {f"lote_{v['ids']['TER-IPA-330']}": "IPA-0020"}
    assert client.post(url, base | {"forma_pago": "CONTADO"} | lote).status_code == 302
    p = Pedido.objects.get(pk=id_)
    assert (p.estado, p.comprobante) == ("FACTURADO", "FACTURA")
    ficha = client.get(url).content.decode()
    for texto in ("Confirmar entrega", "244.07", "43.93", "Pendiente", "45.43", "Contado"):
        assert texto in ficha, texto

    assert client.post(url, {"accion": "entregar"}).status_code == 302
    assert Pedido.objects.get(pk=id_).estado == "ENTREGADO"


def test_boleta_al_contado_sin_selector(web):
    """RF-VEN-19: sin RUC, Boleta y Contado fijo."""
    client, v = web
    id_ = aprobado(v, ("TER-IPA-330", "1", "12"), cliente="ana")
    ficha = client.get(f"/ventas/pedidos/{id_}/").content.decode()
    assert "Boleta" in ficha and 'value="CREDITO"' not in ficha


def test_costos_ocultos_sin_permiso(web, client):
    """Costo de la venta solo con `inventario.costo.ver`."""
    _, v = web
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    client.post(f"/ventas/pedidos/{id_}/", {"accion": "facturar", "almacen": v["almacen"]})
    empresa_id = v["actor"].empresa_id
    vendedor = Usuario.objects.create_user("ventas@andina.pe", "x", empresa_id=empresa_id)
    client.force_login(asignar_rol(vendedor, "Ventas"), BACKEND)
    ficha = client.get(f"/ventas/pedidos/{id_}/").content.decode()
    assert "244.07" in ficha and "45.43" not in ficha


def test_ficha_del_cliente(web):
    """RF-VEN-04: comprado en 90 días, última compra y saldo por cobrar."""
    client, v = web
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    client.post(f"/ventas/pedidos/{id_}/", {"accion": "facturar", "almacen": v["almacen"]})
    ficha = client.get("/ventas/clientes/", {"editar": v["clientes"]["bar"]}).content.decode()
    assert "Comprado en 90 días" in ficha and "Saldo por cobrar" in ficha
    assert ficha.count("S/ 288.00") >= 2
    assert timezone.localdate().isoformat() in ficha


def test_venta_directa(web):
    """RF-VEN-18, 29 y 52 (T7): "Clientes varios" por defecto, pagos dinámicos, un solo
    registro por formulario."""
    client, v = web
    sembrar_metodos_pago(v["actor"].empresa_id, v["actor"].usuario_id, timezone.localdate())
    metodos = {m.nombre: m.id for m in MetodoPago.objects.all()}
    pagina = client.get("/ventas/venta-directa/").content.decode()
    assert "Clientes varios" in pagina and "Yape" in pagina
    token = re.search(r'name="token" value="([^"]+)"', pagina).group(1)
    datos = {
        "cliente": v["clientes"]["varios"],
        "almacen": v["almacen"],
        "producto": v["ids"]["TER-IPA-330"],
        "cantidad": "24",
        "precio": "12",
        "pago_metodo": [metodos["Efectivo"], metodos["Yape"]],
        "pago_monto": ["200.00", "50.00"],
        "token": token,
    }
    error = client.post("/ventas/venta-directa/", datos).content.decode()
    assert "Los pagos (250.00) deben sumar el total (288.00)" in error
    assert f'value="{token}"' in error  # el mismo formulario conserva su token
    datos["pago_monto"] = ["200.00", "88.00"]
    r = client.post("/ventas/venta-directa/", datos)
    p = Pedido.objects.get()
    assert r.status_code == 302 and r["Location"] == f"/ventas/pedidos/{p.id}/"
    assert (p.estado, p.cobranza.estado) == ("ENTREGADO", "PAGADA")
    client.post("/ventas/venta-directa/", datos)  # doble envío
    assert Pedido.objects.count() == 1
