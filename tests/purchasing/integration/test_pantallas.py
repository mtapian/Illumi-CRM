"""0002d, T7: listado de proveedores y pestaña "Compras" de la ficha (RF-COM-01 a 03, 22)."""

from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Producto, Unidad
from purchasing.infrastructure.models import Proveedor, ProveedorProducto
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"
RUC = "20512345671"


@pytest.fixture
def empresa(crear_empresa):
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    admin = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, admin.id, date.today())
    with tenant_context(empresa.id):
        kg = Unidad.objects.get(abreviatura="KG")
        malta = Producto.objects.create(sku="INS-MALTA", nombre="Malta", unidad=kg)
        granel = Producto.objects.create(
            sku="GRA-IPA", nombre="IPA", unidad=kg, se_compra=False, se_fabrica=True
        )
    return {"empresa": empresa, "admin": admin, "malta": malta.id, "granel": granel.id}


def entrar(client, e, rol="Administrador"):
    usuario = e["admin"]
    if rol != "Administrador":
        usuario = Usuario.objects.create_user(f"{rol}@andina.pe", "x", empresa=e["empresa"])
        asignar_rol(usuario, rol)
    client.force_login(usuario, BACKEND)


def test_alta_busqueda_y_edicion_en_su_propia_pagina(client, empresa):
    entrar(client, empresa)
    datos = {"accion": "guardar", "tipo_doc": "RUC", "num_doc": RUC, "razon_social": "Maltería"}
    assert client.post("/compras/proveedores/", datos).status_code == 302
    r = client.post("/compras/proveedores/", datos | {"razon_social": "Otra"})
    assert f"Ya existe un proveedor con el RUC {RUC}" in r.content.decode()
    with tenant_context(empresa["empresa"].id):
        p = Proveedor.objects.get()
    html = client.get("/compras/proveedores/?q=2051").content.decode()
    assert "Maltería" in html and "+ Nuevo proveedor" in html
    assert "Sin resultados" in client.get("/compras/proveedores/?q=zzz").content.decode()
    html = client.get(f"/compras/proveedores/?editar={p.id}").content.decode()
    assert "Editar proveedor" in html and "<table" not in html  # RF-CAT-51


def test_editar_proveedor_de_otra_empresa_da_404(client, empresa, crear_empresa):
    otra = crear_empresa(ruc="20100047218")
    with tenant_context(otra.id):
        ajeno = Proveedor.objects.create(tipo_doc="RUC", num_doc=RUC, razon_social="Ajeno")
    entrar(client, empresa)
    assert client.get(f"/compras/proveedores/?editar={ajeno.id}").status_code == 404
    r = client.post("/compras/proveedores/", {"accion": "eliminar", "id": ajeno.id})
    assert r.status_code == 404


def test_pestana_compras_solo_en_comprables_y_asociar(client, empresa):
    """RF-COM-22: la pestaña se ve al cargar solo si el producto se compra."""
    with tenant_context(empresa["empresa"].id):
        p = Proveedor.objects.create(tipo_doc="RUC", num_doc=RUC, razon_social="Maltería")
    entrar(client, empresa)
    html = client.get(f"/catalogo/productos/{empresa['granel']}/").content.decode()
    assert '<label for="pes-compras" data-activa="no">Compras' in html
    malta = empresa["malta"]
    html = client.get(f"/catalogo/productos/{malta}/").content.decode()
    assert '<label for="pes-compras" data-activa="si">Compras' in html
    asociar = {"producto": malta, "proveedor": p.id, "precio": "4.80", "plazo": "3"}
    r = client.post("/compras/proveedores/producto/", asociar)
    assert r.status_code == 302 and r.url == f"/catalogo/productos/{malta}/"
    html = client.get(r.url).content.decode()
    assert "Maltería" in html and "4.80" in html
    client.post("/compras/proveedores/producto/", asociar | {"accion": "quitar"})
    with tenant_context(empresa["empresa"].id):
        assert not ProveedorProducto.objects.exists()


def test_sin_permiso_ve_la_pestana_pero_no_gestiona(client, empresa):
    """Producción consulta la ficha; asociar exige compras.proveedor.gestionar (art. 6.1)."""
    entrar(client, empresa, "Producción")
    html = client.get(f"/catalogo/productos/{empresa['malta']}/").content.decode()
    assert "Sin proveedores asociados" in html and "Asociar" not in html
    r = client.post("/compras/proveedores/producto/", {"producto": empresa["malta"]})
    assert r.status_code == 403
    assert client.get("/compras/proveedores/").status_code == 403


def test_error_junto_al_campo_y_lo_escrito_vuelve(client, empresa):
    """docs/ux.md §4: el documento duplicado se marca en su campo; la razón social se conserva."""
    entrar(client, empresa)
    datos = {"accion": "guardar", "tipo_doc": "RUC", "num_doc": RUC, "razon_social": "Maltería"}
    client.post("/compras/proveedores/", datos)
    pagina = client.post("/compras/proveedores/?nuevo=1", datos | {"razon_social": "Otra"})
    html = pagina.content.decode()
    error = f'<small class="error-campo" role="alert">Ya existe un proveedor con el RUC {RUC}'
    assert error in html
    assert 'value="Otra"' in html and "No se guardó: revisa el campo marcado." in html
