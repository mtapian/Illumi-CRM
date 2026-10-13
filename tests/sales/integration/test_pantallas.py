"""0006a, T8 y T9: pantallas de clientes y pedidos (RF-VEN-01 a 08, 11, 15, 37, 43 a 48, 50)."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from django.db import transaction
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen
from sales.infrastructure.models import Cliente, Pedido
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import Usuario

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, empresa_ventas):
    empresa, actor = empresa_ventas
    with tenant_context(empresa.id):
        ids = {p.sku: p.id for p in Producto.objects.all()}
        almacen = Almacen.objects.get(nombre="Principal").id
        with transaction.atomic():
            linea = Linea(ids["TER-IPA-330"], almacen, D("48"), D("4"))
            hoy = timezone.localdate()
            inventario().registrar_entrada("COMPRA", "COMPRA", 1, [linea], actor.usuario_id, hoy)
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    return client, empresa, ids


def test_clientes_crear_buscar_editar_y_desactivar(web):
    """RF-VEN-01, 05, RF-VEN-43 (grilla y buscador), 44, 50 y RF-VEN-04 (ficha con pedidos)."""
    client, empresa, _ = web
    datos = {"accion": "guardar", "nombre": "Bar El Lúpulo", "tipo_doc": "RUC"}
    datos |= {"num_doc": "20512345671", "telefono": "987654321", "activo": "on"}
    client.post("/ventas/clientes/", datos)
    with tenant_context(empresa.id):
        bar = Cliente.objects.get(num_doc="20512345671")
    listado = client.get("/ventas/clientes/", {"q": "lúpulo"}).content.decode()
    assert "Bar El Lúpulo" in listado and "Clientes varios" not in listado
    assert "Eliminar" not in client.get("/ventas/clientes/").content.decode()  # CRU
    malo = client.post("/ventas/clientes/", datos | {"num_doc": "20512345670"}).content.decode()
    assert "El RUC no es válido" in malo
    encontrados = client.get("/ventas/clientes/buscar/", {"q": "2051"}).json()["clientes"]
    assert [c["nombre"] for c in encontrados] == ["Bar El Lúpulo"]
    rapido = {"nombre": "Ana Quispe", "tipo_doc": "DNI", "num_doc": "45871236"}
    assert client.post("/ventas/clientes/rapido/", rapido).json()["nombre"] == "Ana Quispe"
    error = client.post("/ventas/clientes/rapido/", rapido | {"num_doc": "1"})
    assert (
        error.status_code == 400
        and "El DNI debe tener 8 dígitos" in error.json()["errores"]["num_doc"]
    )
    client.post("/ventas/clientes/", {"accion": "desactivar", "id": bar.id})
    assert client.get("/ventas/clientes/buscar/", {"q": "lúpulo"}).json()["clientes"] == []
    ficha = client.get("/ventas/clientes/", {"editar": bar.id}).content.decode()
    assert "Pedidos" in ficha


def test_pedido_crear_aprobar_y_vistas(web):
    """RF-VEN-06, 08, 15, 45 a 48 y dos pedidos que comparten el stock."""
    client, empresa, ids = web
    with tenant_context(empresa.id):
        bar = Cliente.objects.create(nombre="Bar El Lúpulo", tipo_doc="RUC", num_doc="20512345671")
    manana = (timezone.localdate() + timedelta(days=5)).isoformat()

    def pedido(lineas, fecha=manana):
        datos = [("cliente", bar.id), ("fecha_entrega", fecha), ("comentario", "")]
        for sku, q in lineas:
            datos += [("producto", ids[sku]), ("cantidad", q), ("precio", "")]
        from urllib.parse import urlencode

        datos = [(k, v if v != "" or k != "precio" else "12") for k, v in datos]
        return client.post(
            "/ventas/pedidos/nuevo/",
            urlencode(datos),
            content_type="application/x-www-form-urlencoded",
        )

    r = pedido([("TER-IPA-330", "60")])
    with tenant_context(empresa.id):
        uno = Pedido.objects.get()
    ficha = client.get(r.url).content.decode()
    assert "P-000001" in ficha and "Quiebre de stock" in ficha and "S/ 720.00" in ficha
    aprobar = client.post(
        r.url,
        {
            "accion": "aprobar",
            "cliente": bar.id,
            "fecha_entrega": manana,
            "producto": ids["TER-IPA-330"],
            "cantidad": "60",
            "precio": "12",
        },
        follow=True,
    )
    assert "Stock insuficiente: TER-IPA-330 faltan 12.0000" in aprobar.content.decode()
    # dos pedidos de 30: cada uno cabe en 48, juntos no; aprobar no reserva (art. 10.3)
    for _ in range(2):
        r = pedido([("TER-IPA-330", "30")])
        client.post(
            r.url,
            {
                "accion": "aprobar",
                "cliente": bar.id,
                "fecha_entrega": manana,
                "producto": ids["TER-IPA-330"],
                "cantidad": "30",
                "precio": "12",
            },
        )
    with tenant_context(empresa.id):
        assert list(Pedido.objects.order_by("numero").values_list("estado", flat=True)) == [
            "CREADO",
            "APROBADO",
            "APROBADO",
        ]
    lista = client.get("/ventas/pedidos/").content.decode()
    assert lista.count("Listo para facturar") == 2 and "Quiebre de stock" in lista
    quiebre = client.get("/ventas/pedidos/", {"quiebre": "1"}).content.decode()
    assert "P-000001" in quiebre and "P-000002" not in quiebre
    kanban = client.get("/ventas/pedidos/", {"vista": "kanban"}).content.decode()
    assert 'data-estado="APROBADO"' in kanban and 'data-estado="CANCELADO"' not in kanban
    inicio = client.get("/dashboard/").content.decode()
    assert "1 pedido con quiebre de stock" in inicio and "/ventas/pedidos/?quiebre=1" in inicio
    client.post(f"/ventas/pedidos/{uno.id}/", {"accion": "cancelar", "motivo": "Desistió"})
    with tenant_context(empresa.id):
        assert Pedido.objects.get(pk=uno.id).estado == "CANCELADO"
    atrasado = pedido([("TER-IPA-330", "1")], fecha=date(2020, 1, 1).isoformat())
    assert "Atrasado" in client.get(atrasado.url).content.decode()
