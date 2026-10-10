"""T13 a T15: listado, formulario por tipo, ficha y API de productos
(RF-CAT-04 a 09, 14; RNF-CAT-01; RF-TEN-48)."""

import time
from datetime import date

import pytest

from catalog.infrastructure.contenedor import sembrar_unidades
from catalog.infrastructure.models import Familia, Producto, Unidad
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
                tipo="ENVASE",
                unidad=und,
                **kw,
            )
            for i in range(n)
        )


def test_filtros_y_paginacion_de_25(client, lucia):
    productos(lucia.empresa_id, 30)
    with tenant_context(lucia.empresa_id):
        familia = Familia.objects.create(nombre="Snacks")
        und = Unidad.objects.get(abreviatura="UND")
        Producto.objects.create(
            sku="MER-PAPA",
            nombre="Papas fritas",
            tipo="MERCADERIA",
            unidad=und,
            precio_venta=4,
            familia=familia,
            stock_minimo=10,
        )
        Producto.objects.create(
            sku="INS-X", nombre="Viejo", tipo="INSUMO", unidad=und, activo=False
        )
    pagina = client.get("/catalogo/productos/").content.decode()
    assert pagina.count("</code></a></td>") == 25 and "Página 1 de 2" in pagina
    assert "MER-PAPA" in client.get("/catalogo/productos/?q=papas").content.decode()
    assert "MER-PAPA" in client.get(f"/catalogo/productos/?familia={familia.id}").content.decode()
    solo = client.get("/catalogo/productos/?tipo=MERCADERIA").content.decode()
    assert "MER-PAPA" in solo and "P-00001" not in solo
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


def test_formulario_por_tipo_y_ficha_bloqueada(client, lucia, inventario):
    insumo = client.get("/catalogo/productos/nuevo/?tipo=INSUMO").content.decode()
    assert 'name="precio_venta"' not in insumo and 'name="sku"' in insumo
    mercaderia = client.get("/catalogo/productos/nuevo/?tipo=MERCADERIA").content.decode()
    assert 'name="precio_venta"' in mercaderia and 'name="controla_lote"' in mercaderia
    client.post(
        "/catalogo/productos/nuevo/?tipo=INSUMO",
        {"sku": "INS-MALTA", "nombre": "Malta", "unidad": "KG", "stock_minimo": "0"},
    )
    with tenant_context(lucia.empresa_id):
        malta = Producto.objects.get(sku="INS-MALTA").id
    inventario.con_movimientos.add(malta)
    ficha = client.get(f"/catalogo/productos/{malta}/").content.decode()
    assert 'name="sku"' in ficha and "disabled" in ficha.split('name="sku"')[1].split(">")[0]


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


def test_formulario_de_terminado_guarda_presentacion_con_5_materiales(client, lucia):
    with tenant_context(lucia.empresa_id):
        und, litro = Unidad.objects.get(abreviatura="UND"), Unidad.objects.get(abreviatura="L")
        granel = Producto.objects.create(
            sku="GRA-IPA", nombre="IPA", tipo="GRANEL", unidad=litro, controla_lote=True
        )
        envases = [
            Producto.objects.create(sku=f"ENV-{i}", nombre=f"E{i}", tipo="ENVASE", unidad=und).id
            for i in range(5)
        ]
        malta = Producto.objects.create(sku="INS-M", nombre="Malta", tipo="INSUMO", unidad=und)
    datos = {
        "sku": "TER-IPA",
        "nombre": "IPA botella",
        "unidad": "UND",
        "stock_minimo": "0",
        "precio_venta": "12.00",
        "vida_util_dias": "120",
        "granel": granel.id,
        "contenido": "0.33",
    }
    for i, e in enumerate(envases):
        datos |= {f"material_{i}": e, f"cantidad_{i}": "0.0417" if i == 4 else "1"}
    client.post("/catalogo/productos/nuevo/?tipo=TERMINADO", datos)
    with tenant_context(lucia.empresa_id):
        assert Producto.objects.get(sku="TER-IPA").presentacion.materiales.count() == 5
    malo = client.post(
        "/catalogo/productos/nuevo/?tipo=TERMINADO",
        datos | {"sku": "TER-2", "material_0": malta.id},
    ).content.decode()
    assert "Escoja una opción válida" in malo or "tipo ENVASE" in malo


def test_pantalla_isc_solo_con_permiso_y_sin_editar_tarifas(client, lucia):
    respuesta = client.post(
        "/catalogo/isc/",
        {
            "accion": "crear",
            "nombre": "Cerveza",
            "codigo_tipo_sistema": "02",
            "monto": "2.51",
            "desde": "2024-07-01",
        },
        follow=True,
    )
    pagina = respuesta.content.decode()
    assert "Cerveza" in pagina and ("2.5100" in pagina or "2,5100" in pagina)
    assert "Agregar tarifa" in pagina
    assert "Editar" not in pagina and "Borrar" not in pagina
    ana = asignar_rol(
        Usuario.objects.create_user("ana@andina.pe", "x", empresa=lucia.empresa), "Gerente"
    )
    client.force_login(ana, BACKEND)
    assert client.get("/catalogo/isc/").status_code == 403
