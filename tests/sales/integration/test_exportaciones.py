"""0008c, T6 y T7: exportar las grillas a XLSX y CSV (RF-FIN-15, 16, 25)."""

import csv
import io
import re
import zipfile

import pytest
from django.utils import timezone

from catalog.infrastructure.models import Producto
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol
from tests.sales.usecases.test_facturacion import preparar

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, empresa_ventas):
    empresa, actor = empresa_ventas
    v = preparar(empresa, actor, timezone.localdate())
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    return client, v


def descargar(respuesta) -> bytes:
    assert respuesta.status_code == 200, respuesta.status_code
    if respuesta.streaming:
        return b"".join(respuesta.streaming_content)
    return respuesta.content


def filas_csv(respuesta) -> list[list[str]]:
    return list(csv.reader(io.StringIO(descargar(respuesta).decode("utf-8-sig"))))


def filas_xlsx(respuesta) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(descargar(respuesta))) as z:
        xml = z.read("xl/worksheets/sheet1.xml").decode()

    def columna(ref):  # "C2" → 2 (las celdas vacías no se escriben)
        letras = re.match(r"[A-Z]+", ref).group()
        return sum((ord(c) - 64) * 26**i for i, c in enumerate(reversed(letras))) - 1

    filas = []
    for fila in re.findall(r"<row [^>]*>(.*?)</row>", xml):
        celdas = re.findall(
            r'<c r="([A-Z]+\d+)"[^>]*>(?:<is><t>([^<]*)</t></is>|<v>([^<]*)</v>)', fila
        )
        valores = {columna(r): a or b for r, a, b in celdas}
        filas.append([valores.get(i, "") for i in range(max(valores, default=-1) + 1)])
    return filas


def test_exportar_productos_con_los_filtros(web):
    """RF-FIN-15: las columnas de la grilla y el filtro aplicado (XLSX y CSV)."""
    client, _ = web
    filas = filas_csv(client.get("/catalogo/productos/", {"q": "IPA", "formato": "csv"}))
    assert filas[0][:3] == ["SKU", "Nombre", "Unidad"] and "Precio" in filas[0]
    assert sorted(f[0] for f in filas[1:]) == ["TER-IPA-20L", "TER-IPA-330"]
    xlsx = filas_xlsx(client.get("/catalogo/productos/", {"q": "330", "formato": "xlsx"}))
    assert xlsx[0][0] == "SKU" and [f[0] for f in xlsx[1:]] == ["TER-IPA-330"]
    pagina = client.get("/catalogo/productos/").content.decode()
    assert "formato=xlsx" in pagina and "formato=csv" in pagina  # botón Exportar


def test_exportar_kardex_sin_costos_sin_permiso(web, client):
    """RF-FIN-16: sin `inventario.costo.ver` no van los costos."""
    _, v = web
    ipa = Producto.objects.get(sku="TER-IPA-330").id
    con = filas_xlsx(client.get("/inventario/kardex/", {"producto": ipa, "formato": "xlsx"}))
    assert "Costo unit." in con[0] and len(con) == 3  # encabezado + 2 entradas por lote
    vendedor = Usuario.objects.create_user("v@andina.pe", "x", empresa_id=v["actor"].empresa_id)
    asignar_rol(vendedor, "Ventas")
    from tenancy.infrastructure.models import Rol, RolPermiso

    rol = Rol.objects.get(nombre="Ventas")
    for p in ("reportes.exportar", "inventario.kardex.ver"):
        RolPermiso.objects.get_or_create(rol=rol, permiso_id=p)
    client.force_login(vendedor, BACKEND)
    sin = filas_csv(client.get("/inventario/kardex/", {"producto": ipa, "formato": "csv"}))
    assert not any("Costo" in c or "Promedio" in c for c in sin[0])


def test_exportar_exige_el_permiso(web, client):
    """RF-FIN-15: `reportes.exportar`."""
    _, v = web
    vendedor = Usuario.objects.create_user("v@andina.pe", "x", empresa_id=v["actor"].empresa_id)
    client.force_login(asignar_rol(vendedor, "Ventas"), BACKEND)
    assert client.get("/catalogo/productos/", {"formato": "xlsx"}).status_code == 403
    assert "formato=xlsx" not in client.get("/catalogo/productos/").content.decode()


def test_tope_de_filas_vuelve_a_la_grilla(web, monkeypatch):
    """RF-FIN-25: con más filas que el tope, no se genera y se avisa."""
    client, _ = web
    from shared.interfaces import exportar

    monkeypatch.setattr(exportar, "TOPE", 1)
    r = client.get("/catalogo/productos/", {"formato": "csv"}, follow=True)
    assert "agrega filtros para exportar" in r.content.decode()
    assert r.redirect_chain and "formato" not in r.redirect_chain[-1][0]


def test_exportar_pedidos_una_fila_por_sku(web):
    """RF-FIN-15: los pedidos van una fila por línea, con los filtros de la grilla."""
    client, v = web
    from tests.sales.usecases.test_facturacion import aprobado

    aprobado(v, ("TER-IPA-330", "24", "12"), ("SRV-FLETE", "1", "20"))
    aprobado(v, ("TER-IPA-330", "1", "12"), cliente="ana")
    filtro = {"cliente": v["clientes"]["bar"], "formato": "xlsx"}
    filas = filas_xlsx(client.get("/ventas/pedidos/", filtro))
    cabecera = filas[0]
    for columna in ("Pedido", "Fecha y hora", "Cliente", "Comprobante", "Estado", "Cobranza"):
        assert columna in cabecera, columna
    sku = cabecera.index("SKU")
    assert sorted(f[sku] for f in filas[1:]) == ["SRV-FLETE", "TER-IPA-330"]
    assert {f[cabecera.index("Pedido")] for f in filas[1:]} == {"P-000001"}
    assert "formato=csv" in client.get("/ventas/pedidos/").content.decode()


def test_exportar_cobranzas(web):
    """RF-FIN-15: las columnas de la grilla de cobranzas."""
    client, v = web
    from sales.infrastructure.contenedor import sembrar_metodos_pago
    from tests.sales.usecases import test_facturacion as tf
    from tests.sales.usecases.test_facturacion import aprobado, facturar

    sembrar_metodos_pago(v["actor"].empresa_id, None, timezone.localdate())
    original, tf.HOY = tf.HOY, timezone.localdate()
    try:
        facturar(v, aprobado(v, ("TER-IPA-330", "24", "12")))
    finally:
        tf.HOY = original
    filas = filas_csv(client.get("/ventas/cobranzas/", {"formato": "csv"}))
    assert filas[0][:3] == ["Cobranza", "Pedido", "Cliente"] and "Saldo" in filas[0]
    assert filas[1][:3] == ["COB-000001", "P-000001", "Bar El Lúpulo"]
    assert filas[1][filas[0].index("Saldo")] == "288.00"
