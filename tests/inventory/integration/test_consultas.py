"""0003c, T3 a T6: stock, kardex, avisos y rendimiento (RF-INV-04 a 07, 14 a 16, 30;
RNF-INV-02; RF-TEN-51)."""

import csv
import io
import time
from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from django.db import transaction
from django.utils import timezone

from catalog.infrastructure.models import Categoria, Producto
from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen, ConfigInventario, Movimiento, Stock
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, inv):
    client.force_login(inv["admin"], BACKEND)
    return client


def entra(inv, producto, cant, costo, almacen=None, lote=None, vence=None):
    with transaction.atomic():
        linea = Linea(inv[producto], almacen or inv["principal"], D(cant), D(costo), lote, vence)
        inventario().registrar_entrada("SALDO_INICIAL", "AJUSTE", 1, [linea], None, date.today())


def fila(html, sku):
    return html.split(f'id="fila-{sku}"')[1].split("</tr>")[0]


def como(client, inv, rol):
    usuario = Usuario.objects.create_user(f"{rol}@andina.pe", "x", empresa=inv["empresa"])
    client.force_login(asignar_rol(usuario, rol), BACKEND)
    return client


def test_stock_con_detalle_valorizacion_y_filtros(web, inv):
    """RF-INV-04, 05 y 16."""
    hoy = timezone.localdate()
    with tenant_context(inv["empresa"].id):
        cervezas = Categoria.objects.create(nombre="Cervezas")
        Producto.objects.filter(pk=inv["ipa"]).update(categoria=cervezas)
        taproom = Almacen.objects.create(nombre="Taproom").id
    entra(inv, "ipa", "10", "4", lote="V", vence=hoy - timedelta(days=1))
    entra(inv, "ipa", "20", "4", almacen=taproom, lote="B", vence=hoy + timedelta(days=90))
    entra(inv, "malta", "5", "2")
    html = web.get("/inventario/stock/").content.decode()
    ipa = fila(html, "TER-IPA-330")
    assert "30 UND" in ipa and "4.000000" in ipa and "120.00" in ipa
    assert "Principal · lote V" in ipa and "Vencido" in ipa and "Taproom · lote B" in ipa
    assert 'id="categoria-cervezas"><td>Cervezas</td><td>120.00' in html
    assert 'id="categoria-sin-categoria"><td>Sin categoría</td><td>10.00' in html
    assert "<strong>130.00</strong>" in html
    solo_taproom = web.get(f"/inventario/stock/?almacen={taproom}").content.decode()
    assert "20 UND" in fila(solo_taproom, "TER-IPA-330") and "80.00" in solo_taproom
    fabricados = web.get("/inventario/stock/?casilla=se_fabrica").content.decode()
    assert "TER-IPA-330" in fabricados and "INS-MALTA" not in fabricados
    assert "SRV-TOUR" not in html  # un servicio no lleva stock


def test_sin_permiso_de_costos_no_se_ven(client, inv, web):
    """RF-TEN-51: ni en stock ni en kardex ni en el CSV."""
    entra(inv, "malta", "5", "2.5")
    como(client, inv, "Ventas")
    html = client.get("/inventario/stock/").content.decode()
    assert "5 KG" in fila(html, "INS-MALTA") and "2.5" not in fila(html, "INS-MALTA")
    assert "Valorización" not in html


def test_kardex_filtros_saldos_cursor_y_csv(web, inv):
    """RF-INV-06 y 07."""
    for _ in range(55):
        entra(inv, "malta", "1", "2")
    entra(inv, "ipa", "3", "4")
    todos = web.get("/inventario/kardex/").content.decode()
    assert "<th>Saldo</th>" not in todos and "Siguientes" in todos
    malta = web.get(f"/inventario/kardex/?producto={inv['malta']}").content.decode()
    assert "<th>Saldo</th>" in malta and "<td>TER-IPA-330</td>" not in malta
    with tenant_context(inv["empresa"].id):
        corte = Movimiento.objects.filter(producto_id=inv["malta"]).order_by("id")[49].id
    resto = web.get(f"/inventario/kardex/?producto={inv['malta']}&despues={corte}")
    assert resto.content.decode().count("<td>SALDO_INICIAL</td>") == 5
    respuesta = web.get(f"/inventario/kardex/?producto={inv['malta']}&formato=csv")
    filas = list(csv.reader(io.StringIO(respuesta.content.decode())))
    assert filas[0][-4:] == ["costo_unitario", "costo_total", "saldo", "promedio"]
    assert len(filas) == 56 and filas[-1][-2:] == ["55.0000", "2.000000"]


def test_avisos_del_dashboard(client, web, inv):
    """RF-INV-14 a 16 y 30."""
    hoy = timezone.localdate()
    with tenant_context(inv["empresa"].id):
        Producto.objects.filter(pk=inv["malta"]).update(stock_minimo=10)
        ConfigInventario.objects.create(dias_alerta_vencimiento=45)
    entra(inv, "malta", "10", "2")  # igual al mínimo: stock bajo
    entra(inv, "ipa", "5", "4", lote="PRONTO", vence=hoy + timedelta(days=44))
    entra(inv, "ipa", "5", "4", lote="LEJOS", vence=hoy + timedelta(days=46))
    entra(inv, "ipa", "5", "4", lote="VIEJO", vence=hoy - timedelta(days=2))
    html = web.get("/dashboard/").content.decode()
    assert "INS-MALTA · Malta</a>: 10 de 10" in html
    assert "lote PRONTO (5):\n  44 días restantes" in html
    assert 'data-lote="VIEJO"' in html and "Vencido" in html and "LEJOS" not in html
    sin_stock = Usuario.objects.create_user("x@andina.pe", "x", empresa=inv["empresa"])
    client.force_login(sin_stock, BACKEND)  # sin roles: sin inventario.stock.ver
    assert "Stock bajo" not in client.get("/dashboard/").content.decode()


@pytest.mark.parametrize("ruta", ["/inventario/stock/", "/inventario/kardex/?producto={malta}"])
def test_rendimiento_con_100000_movimientos(web, inv, ruta):
    """RNF-INV-02: p95 < 800 ms con 100 000 movimientos en la empresa."""
    with tenant_context(inv["empresa"].id):
        base = {"tipo": "ENTRADA", "motivo": "COMPRA", "almacen_id": inv["principal"]}
        base |= {"costo_unitario": D("1"), "costo_total": D("1"), "ref_tipo": "COMPRA"}
        Movimiento.objects.bulk_create(
            (
                Movimiento(
                    empresa_id=inv["empresa"].id,
                    producto_id=inv["malta"] if i % 2 else inv["ipa"],
                    cantidad=D("1"),
                    saldo_cantidad=D(i),
                    saldo_promedio=D("1"),
                    **base,
                )
                for i in range(100_000)
            ),
            batch_size=5_000,
        )
        Stock.objects.create(producto_id=inv["malta"], almacen_id=inv["principal"], cantidad=50_000)
    url = ruta.format(malta=inv["malta"])
    tiempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        assert web.get(url).status_code == 200
        tiempos.append(time.perf_counter() - inicio)
    assert sorted(tiempos)[18] < 0.8
