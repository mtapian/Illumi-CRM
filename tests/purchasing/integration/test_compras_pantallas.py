"""0004a, T6 y T7: pantalla de compra con líneas dinámicas, listado, detalle y enlace desde el
kardex (RF-COM-04, 13, 14, 25 a 27)."""

from decimal import Decimal as D

import pytest
from django.utils import timezone

from catalog.infrastructure.models import Producto, Unidad
from inventory.infrastructure.models import Almacen, CostoProducto
from purchasing.infrastructure.models import Compra, Proveedor
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"
HOY = timezone.localdate().isoformat()


@pytest.fixture
def e(client, empresa_compras):
    empresa, _ = empresa_compras
    client.force_login(Usuario.objects.get(email="lucia@andina.pe"), BACKEND)
    und = Unidad.objects.get(abreviatura="UND")
    botella = Producto.objects.create(sku="ENV-BOT330", nombre="Botella", unidad=und)
    tapa = Producto.objects.create(sku="ENV-TAPA", nombre="Tapa", unidad=und)
    proveedor = Proveedor.objects.create(
        tipo_doc="RUC", num_doc="20512345671", razon_social="Maltería del Sur"
    )
    return {
        "empresa": empresa,
        "proveedor": proveedor.id,
        "almacen": Almacen.objects.get().id,
        "productos": [Producto.objects.get(sku="INS-MALTA").id, botella.id, tapa.id],
    }


def formulario(e, cantidades=("50", "1200", "1200"), costos=("5", "0.85", "0.10"), **kw):
    n = len(cantidades)
    return {
        "proveedor": e["proveedor"],
        "fecha": HOY,
        "almacen": e["almacen"],
        "doc_tipo": "FACTURA",
        "doc_serie_numero": "F001-000845",
        "observacion": "",
        "producto": e["productos"][:n],
        "cantidad": list(cantidades),
        "costo": list(costos),
        "bonificacion": [""] * n,
        "lote": [""] * n,
        "vencimiento": [""] * n,
    } | kw


def test_crear_editar_pasar_y_finalizar_desde_la_pantalla(client, e):
    r = client.post("/compras/nueva/", formulario(e))
    compra = Compra.objects.get()
    assert r.status_code == 302 and r.url == f"/compras/{compra.id}/"
    assert (compra.estado, compra.total, compra.lineas.count()) == ("CREADA", D("1640.20"), 3)
    pagina = client.get(f"/compras/{compra.id}/").content.decode()
    # Reglas de UX: la acción principal es el siguiente paso; Guardar solo con cambios.
    assert 'aria-current="step" class="actual">Creada' in pagina and "Pasar a en proceso" in pagina
    assert "Finalizar y recibir stock" not in pagina and "data-con-cambios disabled" in pagina
    datos = formulario(e, ("40", "1200"), ("5", "0.85"), accion="en_proceso")
    client.post(f"/compras/{compra.id}/", datos)
    compra.refresh_from_db()
    assert (compra.estado, compra.lineas.count(), compra.subtotal) == (
        "EN_PROCESO",
        2,
        D("1220.00"),
    )
    pagina = client.get(f"/compras/{compra.id}/").content.decode()
    assert "Finalizar y recibir stock" in pagina and "Pasar a en proceso" not in pagina
    assert 'id="confirmar-recepcion"' in pagina and "Maltería del Sur" in pagina  # qué se recibe
    recepcion = {"accion": "finalizar", "almacen_recepcion": e["almacen"]}
    client.post(f"/compras/{compra.id}/", recepcion | {"fecha_recepcion": HOY, "guia": "T001-1"})
    compra.refresh_from_db()
    assert (compra.estado, compra.guia_remision) == ("FINALIZADA", "T001-1")
    assert CostoProducto.objects.get(producto_id=e["productos"][0]).cantidad_total == D("40")
    detalle = client.get(f"/compras/{compra.id}/").content.decode()
    assert 'id="recepcion"' in detalle and "Ver recepción" in detalle
    assert "confirmar-recepcion" not in detalle and "Guardar cambios" not in detalle
    kardex = client.get("/inventario/kardex/").content.decode()
    assert f'href="/compras/{compra.id}/"' in kardex


def test_si_se_rechaza_las_lineas_vuelven(client, e):
    r = client.post("/compras/nueva/", formulario(e, costos=("5", "0", "0.10")))
    pagina = r.content.decode()
    assert "El costo unitario debe ser mayor a 0" in pagina
    assert 'value="1200"' in pagina and 'value="0.10"' in pagina
    assert not Compra.objects.exists()


def test_listado_con_filtros(client, e):
    client.post("/compras/nueva/", formulario(e))
    client.post("/compras/nueva/", formulario(e, doc_tipo="BOLETA", doc_serie_numero="B002-7"))
    assert Compra.objects.count() == 2

    def listado(consulta):
        return client.get("/compras/?" + consulta).content.decode()

    assert "C-000001" in listado("q=c-000001") and "C-000002" not in listado("q=c-000001")
    assert "C-000002" in listado("q=b002") and "C-000001" not in listado("q=b002")
    assert "No hay compras con esos filtros" in listado("estado=FINALIZADA")
    assert "C-000002" in listado(f"proveedor={e['proveedor']}&desde=no-es-fecha")


def test_sin_permiso_de_compras_no_entra(client, e):
    ventas = Usuario.objects.create_user("v@andina.pe", "x", empresa=e["empresa"])
    asignar_rol(ventas, "Ventas")
    client.force_login(ventas, BACKEND)
    assert client.get("/compras/").status_code == 403
    assert client.get("/compras/nueva/").status_code == 403


def test_anular_desde_la_pantalla(client, e):
    """0004b, T5 (RF-COM-15, 16, 28): en "Más acciones", con motivo; Almacén no lo ve."""
    client.post("/compras/nueva/", formulario(e))
    compra = Compra.objects.get()
    url = f"/compras/{compra.id}/"
    assert "Anular compra" in client.get(url).content.decode()
    rosa = Usuario.objects.create_user("rosa@andina.pe", "x", empresa=e["empresa"])
    asignar_rol(rosa, "Almacén")
    client.force_login(rosa, BACKEND)
    assert "Anular compra" not in client.get(url).content.decode()
    r = client.post(url, {"accion": "anular", "motivo": "x"}, follow=True)
    assert "Acceso denegado" in r.content.decode()
    client.force_login(Usuario.objects.get(email="lucia@andina.pe"), BACKEND)
    r = client.post(url, {"accion": "anular", "motivo": "Pedido cancelado"}, follow=True)
    pagina = r.content.decode()
    assert "Compra anulada." in pagina and "Motivo: Pedido cancelado" in pagina
    assert "Anular compra" not in pagina
    compra.refresh_from_db()
    assert compra.estado == "ANULADA"
