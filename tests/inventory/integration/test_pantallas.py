"""0003a, T16: pantalla de almacenes (RF-INV-02, 03)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import transaction

from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen
from shared.domain.tenant import tenant_context

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, inv):
    client.force_login(inv["admin"], BACKEND)
    return client


def test_crear_buscar_y_editar_en_su_propia_pagina(web, inv):
    assert (
        web.post("/inventario/almacenes/", {"accion": "guardar", "nombre": "Taproom"}).status_code
        == 302
    )
    r = web.post("/inventario/almacenes/", {"accion": "guardar", "nombre": "taproom"})
    assert "Ya existe el almacén taproom" in r.content.decode()
    html = web.get("/inventario/almacenes/?q=tap").content.decode()
    assert "Taproom" in html and "Principal" not in html
    html = web.get(f"/inventario/almacenes/?editar={inv['principal']}").content.decode()
    assert "Editar almacén" in html and "<table" not in html


def test_con_stock_no_se_desactiva_y_otra_empresa_da_404(web, inv, crear_empresa):
    with transaction.atomic():
        linea = Linea(inv["malta"], inv["principal"], D("1"), D("4"))
        inventario().registrar_entrada("SALDO_INICIAL", "AJUSTE", 1, [linea], None, date.today())
    html = web.get("/inventario/almacenes/").content.decode()
    assert "Desactivar" not in html  # con stock no se ofrece
    r = web.post("/inventario/almacenes/", {"accion": "desactivar", "id": inv["principal"]})
    assert "El almacén tiene stock" in r.content.decode()
    otra = crear_empresa(ruc="20100047218")
    with tenant_context(otra.id):
        ajeno = Almacen.objects.create(nombre="Ajeno").id
    assert web.get(f"/inventario/almacenes/?editar={ajeno}").status_code == 404
    assert (
        web.post("/inventario/almacenes/", {"accion": "desactivar", "id": ajeno}).status_code == 404
    )


def test_conteo_de_tres_lineas_y_detalle(web, inv):
    """T9, RF-INV-08 y RF-INV-11: un conteo de 3 líneas desde la pantalla."""
    with transaction.atomic():
        for p in ("malta", "ipa"):
            linea = Linea(inv[p], inv["principal"], D("10"), D("4"))
            inventario().registrar_entrada(
                "SALDO_INICIAL", "AJUSTE", 1, [linea], None, date.today()
            )
    datos = {"tipo": "CONTEO", "almacen": inv["principal"], "motivo": "Inventario mensual"}
    # Una línea por producto, todas las que hagan falta (PO, 2026-10-10): listas alineadas.
    datos |= {
        "producto": [inv["malta"], inv["ipa"], inv["ipa"]],
        "cantidad": ["8", "10", "3"],
        "lote": ["", "", "NUEVO"],
        "vencimiento": ["", "", ""],
        "costo": ["", "", "4"],
        "sentido": ["", "", ""],
    }
    r = web.post("/inventario/ajustes/", datos)
    assert r.status_code == 302, r.content.decode()[:500]
    html = web.get(r.url).content.decode()
    assert "Ajuste N.° 1" in html and "Inventario mensual" in html and "Anular" in html
    assert f'<a href="{r.url}">1</a>' in web.get("/inventario/ajustes/").content.decode()


def test_sin_permiso_de_anular_no_ve_el_boton_ni_puede(client, inv, web):
    from tenancy.infrastructure.models import Usuario
    from tests.conftest import asignar_rol

    with transaction.atomic():
        linea = Linea(inv["malta"], inv["principal"], D("10"), D("4"))
        inventario().registrar_entrada("SALDO_INICIAL", "AJUSTE", 1, [linea], None, date.today())
    datos = {"tipo": "MERMA", "almacen": inv["principal"], "motivo": "Saco roto"}
    linea = {"producto": inv["malta"], "cantidad": "1", "lote": "", "vencimiento": ""}
    r = web.post("/inventario/ajustes/", datos | linea | {"costo": "", "sentido": ""})
    almacen = Usuario.objects.create_user("al@andina.pe", "x", empresa=inv["empresa"])
    client.force_login(asignar_rol(almacen, "Almacén"), BACKEND)
    assert "Anular" not in client.get(r.url).content.decode()
    assert client.post(r.url, {"motivo": "x"}).status_code == 403


def test_lineas_dinamicas_sin_limite_y_se_conservan_si_hay_error(web, inv):
    """0003b, plan §6 (PO, 2026-10-10): se arranca con una línea, se agregan con un botón
    sin límite y, si el ajuste se rechaza, las líneas ingresadas vuelven a mostrarse."""
    html = web.get("/inventario/ajustes/").content.decode()
    assert html.count('name="producto"') == 2  # la línea inicial y la plantilla para agregar
    assert "+ Agregar producto" in html and "<template" in html
    n = 15
    datos = {"tipo": "SALDO_INICIAL", "almacen": inv["principal"], "motivo": "Apertura"}
    datos |= {"producto": [inv["malta"]] * n, "cantidad": ["1"] * n, "lote": [""] * n}
    datos |= {"vencimiento": [""] * n, "costo": [""] * n, "sentido": [""] * n}
    r = web.post("/inventario/ajustes/", datos)  # sin costo: se rechaza
    html = r.content.decode()
    assert "requiere un costo unitario mayor a 0" in html
    assert html.count(f'<option value="{inv["malta"]}" selected>') == n
