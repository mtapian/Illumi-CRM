"""T13 a T15: listado, formulario por tipo, ficha y API de productos
(RF-CAT-04 a 09, 14; RNF-CAT-01; RF-TEN-48)."""

import time
from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import (
    Categoria,
    Marca,
    Producto,
    ProductoIscTasa,
    Unidad,
)
from catalog.interfaces.pestanas import pestanas
from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from tenancy.application.tokens import CrearTokenApi
from tenancy.infrastructure.contenedor import actor_de, caso_de_tokens
from tenancy.infrastructure.models import PlanFuncionalidad, Rol, Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def lucia(client, crear_empresa):
    empresa = crear_empresa()
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    usuario = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    sembrar_unidades(empresa.id, usuario.id, date.today())
    client.force_login(usuario, BACKEND)
    return usuario


def productos(empresa_id, n, **kw):
    with tenant_context(empresa_id):
        und = Unidad.objects.get(abreviatura="UND")
        Producto.objects.bulk_create(
            Producto(
                empresa_id=empresa_id,
                sku=f"P-{i:05d}",
                nombre=f"Producto {i}",
                tipo="BIEN",
                unidad=und,
                **kw,
            )
            for i in range(n)
        )


def test_filtros_y_paginacion_de_25(client, lucia):
    productos(lucia.empresa_id, 30)
    with tenant_context(lucia.empresa_id):
        categoria = Categoria.objects.create(nombre="Snacks", descripcion="Snacks y piqueos")
        und = Unidad.objects.get(abreviatura="UND")
        Producto.objects.create(
            sku="MER-PAPA",
            nombre="Papas fritas",
            tipo="BIEN",
            se_vende=True,
            unidad=und,
            precio_venta=4,
            categoria=categoria,
            stock_minimo=10,
        )
        Producto.objects.create(sku="INS-X", nombre="Viejo", tipo="BIEN", unidad=und, activo=False)
    pagina = client.get("/catalogo/productos/").content.decode()
    assert pagina.count("</code></a></td>") == 25 and "Página 1 de 2" in pagina
    assert "MER-PAPA" in client.get("/catalogo/productos/?q=papas").content.decode()
    assert (
        "MER-PAPA" in client.get(f"/catalogo/productos/?categoria={categoria.id}").content.decode()
    )
    assert "Categoría" in pagina
    assert "familia" not in pagina.lower()
    assert client.get("/catalogo/categorias/").status_code == 200
    solo = client.get("/catalogo/productos/?casilla=se_vende").content.decode()
    assert "MER-PAPA" in solo and "P-00001" not in solo
    assert "MER-PAPA" not in client.get("/catalogo/productos/?tipo=SERVICIO").content.decode()
    assert (
        "INS-X" not in pagina
        and "INS-X" in client.get("/catalogo/productos/?estado=inactivos").content.decode()
    )
    bajos = client.get("/catalogo/productos/?stock_bajo=1").content.decode()
    assert "MER-PAPA" in bajos and "P-00001" not in bajos


def test_busqueda_con_10000_productos_en_menos_de_800_ms(client, lucia):
    """RNF-CAT-01: p95 < 800 ms con 10 000 productos."""
    productos(lucia.empresa_id, 10_000)
    tiempos = []
    for i in range(20):
        inicio = time.perf_counter()
        assert client.get(f"/catalogo/productos/?q=Producto {i * 37}").status_code == 200
        tiempos.append(time.perf_counter() - inicio)
    assert sorted(tiempos)[18] < 0.8


def test_formulario_con_tipo_casillas_y_ficha_bloqueada(client, lucia, inventario):
    """RF-CAT-37, 38, 43: tipo y casillas arriba; con movimientos, SKU, tipo y unidad fijos."""
    nuevo = client.get("/catalogo/productos/nuevo/").content.decode()
    assert 'name="se_vende"' in nuevo and 'name="tipo"' in nuevo and 'name="peso_kg"' in nuevo
    assert 'for="pes-ventas" data-activa="no"' in nuevo  # se compra por defecto, no se vende
    assert 'name="controla_lote"' not in nuevo  # el lote no es del producto (RF-CAT-40)
    servicio = client.get("/catalogo/productos/nuevo/?tipo=SERVICIO").content.decode()
    assert 'for="pes-ventas" data-activa="si"' in servicio
    assert 'for="pes-inventario" data-activa="no"' in servicio
    client.post(
        "/catalogo/productos/nuevo/",
        {"tipo": "BIEN", "se_compra": "on", "sku": "INS-MALTA", "nombre": "Malta", "unidad": "KG"},
    )
    with tenant_context(lucia.empresa_id):
        malta = Producto.objects.get(sku="INS-MALTA").id
    inventario.con_movimientos.add(malta)
    ficha = client.get(f"/catalogo/productos/{malta}/").content.decode()
    for campo in ('name="sku"', 'name="tipo"'):
        assert "disabled" in ficha.split(campo)[1].split(">")[0]


def test_api_de_productos_solo_de_su_empresa(client, lucia, crear_empresa):
    productos(lucia.empresa_id, 3)
    otra = crear_empresa(ruc="20100047218")
    otro = asignar_rol(Usuario.objects.create_user("x@b.pe", "x", empresa=otra))
    sembrar_unidades(otra.id, otro.id, date.today())
    productos(otra.id, 2)
    almacen = Rol.all_tenants.get(empresa_id=lucia.empresa_id, nombre="Almacén").id
    token = caso_de_tokens(CrearTokenApi).ejecutar(
        actor_de(lucia, date.today()), "n8n", "n8n", [almacen], date.today()
    )
    client.logout()
    datos = client.get("/api/v1/productos/", HTTP_AUTHORIZATION=f"Token {token}").json()
    assert datos["count"] == 3 and {"next", "results"} <= set(datos)


def test_formulario_guarda_la_receta_con_varios_componentes(client, lucia):
    """RF-CAT-41: cualquier producto activo como componente, incluso un servicio."""
    with tenant_context(lucia.empresa_id):
        und, litro = Unidad.objects.get(abreviatura="UND"), Unidad.objects.get(abreviatura="L")
        granel = Producto.objects.create(
            sku="GRA-IPA", nombre="IPA", unidad=litro, se_compra=False, se_fabrica=True
        )
        envases = [
            Producto.objects.create(sku=f"ENV-{i}", nombre=f"E{i}", unidad=und).id for i in range(4)
        ]
    datos = {
        "tipo": "BIEN",
        "se_vende": "on",
        "se_fabrica": "on",
        "sku": "TER-IPA",
        "nombre": "IPA botella",
        "unidad": "UND",
        "precio_venta": "12.00",
        "componente_0": granel.id,
        "cantidad_0": "0.33",
    }
    for i, e in enumerate(envases, start=1):
        datos |= {f"componente_{i}": e, f"cantidad_{i}": "0.0417" if i == 4 else "1"}
    client.post("/catalogo/productos/nuevo/", datos)
    with tenant_context(lucia.empresa_id):
        ipa = Producto.objects.get(sku="TER-IPA")
        assert ipa.receta.count() == 5
    ficha = client.get(f"/catalogo/productos/{ipa.id}/").content.decode()
    assert 'for="pes-produccion" data-activa="si"' in ficha
    repetido = client.post(
        "/catalogo/productos/nuevo/", datos | {"sku": "TER-2", "componente_1": granel.id}
    ).content.decode()
    assert "Un componente está repetido en la receta" in repetido


def test_isc_en_la_ficha_con_tasas_y_solo_con_permiso(client, lucia):
    """RF-CAT-45, 46: el ISC se configura en la pestaña Ventas; ya no hay pantalla de
    categorías; sin `catalogo.isc.gestionar` los campos se ven bloqueados."""
    datos = {
        "tipo": "BIEN",
        "se_vende": "on",
        "sku": "MER-CERV",
        "nombre": "Cerveza de terceros",
        "unidad": "UND",
        "precio_venta": "12.00",
        "afecto_isc": "on",
        "isc_codigo_tipo_sistema": "02",
        "contenido_litros": "0.33",
        "tasa_monto": "2.51",
        "tasa_desde": "2024-07-01",
    }
    pagina = client.post("/catalogo/productos/nuevo/", datos, follow=True).content.decode()
    assert "2.5100" in pagina and "2,5100" not in pagina and "Vigente hoy" in pagina
    assert "valor 9.34 + ISC 0.83 + IGV 1.83" in pagina  # RF-CAT-30
    with tenant_context(lucia.empresa_id):
        assert ProductoIscTasa.objects.count() == 1
        merca = Producto.objects.get(sku="MER-CERV").id
    assert client.get("/catalogo/isc/").status_code == 404
    ana = asignar_rol(
        Usuario.objects.create_user("ana@andina.pe", "x", empresa=lucia.empresa), "Gerente"
    )
    client.force_login(ana, BACKEND)
    ficha = client.get(f"/catalogo/productos/{merca}/").content.decode()
    assert "disabled" in ficha.split('name="afecto_isc"')[1].split(">")[0]


def test_ficha_muestra_pestanas_del_tipo_y_las_externas_registradas(client, lucia):
    """T21 y T22: pestañas por tipo y registro externo (RF-CAT-04)."""
    with tenant_context(lucia.empresa_id):
        und = Unidad.objects.get(abreviatura="UND")
        envase = Producto.objects.create(sku="ENV-1", nombre="Botella", unidad=und)
        merca = Producto.objects.create(
            sku="MER-1", nombre="Agua", tipo="BIEN", se_vende=True, unidad=und, precio_venta=2
        )
    pestanas.agregar("prueba", "Prueba", "se_compra", lambda r, i: f"<p>externa {i}</p>")
    try:
        html = client.get(f"/catalogo/productos/{envase.id}/").content.decode()
        assert f"externa {envase.id}" in html and 'for="pes-prueba" data-activa="si"' in html
        assert 'for="pes-ventas" data-activa="no"' in html
        html = client.get(f"/catalogo/productos/{merca.id}/").content.decode()
        assert 'for="pes-ventas" data-activa="si"' in html
        assert "S/ 2.00 = valor 1.69 + IGV 0.31" in html  # RF-CAT-30, sin ISC
    finally:
        pestanas.quitar("prueba")


def test_listado_de_maestro_busca_cuenta_y_no_edita_lo_ajeno(client, lucia, crear_empresa):
    """T27: RF-CAT-36 (patrón de listado) y aislamiento del `?editar=`."""
    with tenant_context(lucia.empresa_id):
        gloria = Marca.objects.create(nombre="Gloria")
        Marca.objects.create(nombre="Nestlé")
        und = Unidad.objects.get(abreviatura="UND")
        Producto.objects.create(sku="M-1", nombre="Leche", tipo="BIEN", unidad=und, marca=gloria)
    html = client.get("/catalogo/marcas/", {"q": "glo"}).content.decode()
    assert "<strong>Gloria</strong>" in html and "Nestlé" not in html
    assert '<span class="chip neutro">1</span>' in html and 'value="desactivar"' in html
    assert "Inicio" in html and "+ Nueva marca" in html
    otra = crear_empresa("Otra")
    with tenant_context(otra.id):
        ajena = Marca.objects.create(nombre="Ajena").id
    assert client.get(f"/catalogo/marcas/?editar={ajena}").status_code == 404
    html = client.get(f"/catalogo/unidades/?editar={und.id}").content.decode()
    assert 'value="UND"' in html and "readonly" in html  # en uso: abreviatura fija (RF-CAT-35)


def test_editar_categoria_en_su_propia_pagina(client, lucia):
    """T43: RF-CAT-50, 51 (referencia del PO "Editar categoría")."""
    with tenant_context(lucia.empresa_id):
        abarrotes = Categoria.objects.create(nombre="Abarrotes")
    html = client.get(f"/catalogo/categorias/?editar={abarrotes.id}").content.decode()
    assert "Editar categoría" in html and 'name="descripcion"' in html
    assert "Categoría activa" in html and "<table" not in html  # solo el formulario
    assert 'aria-current="page">Editar<' in html
    datos = {"accion": "guardar", "id": abarrotes.id, "nombre": "Abarrotes", "descripcion": "Secos"}
    client.post(f"/catalogo/categorias/?editar={abarrotes.id}", datos)  # sin "activo": desactiva
    abarrotes.refresh_from_db()
    assert (abarrotes.descripcion, abarrotes.activo) == ("Secos", False)
    nueva = client.get("/catalogo/categorias/?nuevo=1").content.decode()
    assert "Nueva categoría" in nueva and "<table" not in nueva


def test_sin_permiso_de_isc_no_se_sugiere_el_contenido(client, lucia):
    """RF-CAT-45: el contenido sugerido desde la receta solo se ofrece a quien puede editarlo;
    en un campo bloqueado se enviaría igual y el guardado se rechazaría por falta de permiso."""
    with tenant_context(lucia.empresa_id):
        litro = Unidad.objects.get(abreviatura="L")
        granel = Producto.objects.create(
            sku="GRA-IPA", nombre="IPA", unidad=litro, se_compra=False, se_fabrica=True
        )
        ipa = Producto.objects.create(
            sku="TER-IPA",
            nombre="IPA",
            unidad=Unidad.objects.get(abreviatura="UND"),
            se_compra=False,
            se_fabrica=True,
            se_vende=True,
            precio_venta=12,
        )
        ipa.receta.create(componente=granel, cantidad_por_unidad="0.33")

    def contenido(html):
        return html.split('name="contenido_litros"')[1].split(">")[0]

    assert 'value="0.33' in contenido(client.get(f"/catalogo/productos/{ipa.id}/").content.decode())
    produccion = Usuario.objects.create_user("pro@andina.pe", "x", empresa=lucia.empresa)
    client.force_login(asignar_rol(produccion, "Producción"), BACKEND)
    campo = contenido(client.get(f"/catalogo/productos/{ipa.id}/").content.decode())
    assert "disabled" in campo and "value=" not in campo
