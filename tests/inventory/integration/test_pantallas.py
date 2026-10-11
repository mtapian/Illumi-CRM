"""0003a, T16: pantalla de almacenes (RF-INV-02, 03)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import transaction

from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import PlanFuncionalidad

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, inv):
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=inv["empresa"].plan, funcionalidad_id=f)
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
