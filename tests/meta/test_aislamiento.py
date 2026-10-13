"""T11: aislamiento entre empresas (RF-TEN-52, RNF-TEN-05; constitución, art. 3.2).

1. Todo modelo de negocio (`TenantModel`) se consulta filtrado por la empresa actual.
2. Toda ruta de empresa con un identificador responde 404 con un id de otra empresa.
   Cada ruta nueva con `<int:…>` debe agregarse a `RUTAS`: si no, el test falla.
"""

import pytest
from django.apps import apps
from django.urls import URLPattern, URLResolver, get_resolver

from shared.domain.accesos import CATALOGO
from shared.domain.tenant import TenantNoDefinido, tenant_context
from shared.infrastructure.tenant_models import TenantModel
from tenancy.infrastructure.models import PlanFuncionalidad, Rol, Usuario
from tests.conftest import asignar_rol

BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"
EXCLUIDAS = ("plataforma/", "password-reset/")  # datos de plataforma (art. 3.1) y token


def _ajeno_usuario(otra):
    return Usuario.objects.create_user("x@brew.pe", "x", empresa=otra).id


def _ajeno_rol(otra):
    return Rol.all_tenants.create(empresa=otra, nombre="Ajeno").id


def _ajeno_producto(otra):
    from catalog.infrastructure.models import Producto, Unidad

    unidad = Unidad.all_tenants.create(
        empresa=otra, nombre="U", abreviatura="UND", codigo_sunat="NIU"
    )
    return Producto.all_tenants.create(
        empresa=otra, sku="AJENO", nombre="Ajeno", tipo="BIEN", unidad=unidad
    ).id


def _ajeno_ajuste(otra):
    from inventory.infrastructure.models import Ajuste, Almacen

    almacen = Almacen.all_tenants.create(empresa=otra, nombre="Ajeno")
    return Ajuste.all_tenants.create(
        empresa=otra, numero=1, tipo="MERMA", motivo="x", almacen=almacen
    ).id


def _ajeno_compra(otra):
    from datetime import date

    from inventory.infrastructure.models import Almacen
    from purchasing.infrastructure.models import Compra, Proveedor

    proveedor = Proveedor.all_tenants.create(
        empresa=otra, tipo_doc="RUC", num_doc="20512345671", razon_social="Ajeno"
    )
    almacen = Almacen.all_tenants.create(empresa=otra, nombre="Ajeno")
    return Compra.all_tenants.create(
        empresa=otra,
        numero=1,
        proveedor=proveedor,
        fecha=date.today(),
        almacen=almacen,
        doc_tipo="SIN_DOCUMENTO",
        igv_pct=18,
    ).id


# ruta → función que crea un registro de la otra empresa y devuelve su id
def _ajeno_op(otra):
    from inventory.infrastructure.models import Almacen
    from production.infrastructure.models import OpSalida, OrdenProduccion

    almacen = Almacen.all_tenants.create(empresa=otra, nombre="Ajeno OP")
    op = OrdenProduccion.all_tenants.create(
        empresa=otra,
        numero=1,
        fecha_programada="2026-10-12",
        almacen_origen=almacen,
        almacen_destino=almacen,
    )
    OpSalida.all_tenants.create(empresa=otra, op=op, producto_id=_ajeno_producto(otra), cantidad=1)
    return op.id


def _ajeno_pedido(otra):
    from sales.infrastructure.models import Cliente, Pedido

    cliente = Cliente.all_tenants.create(empresa=otra, nombre="Ajeno", tipo_doc="SD")
    return Pedido.all_tenants.create(
        empresa=otra, numero=1, cliente=cliente, fecha_entrega="2026-11-10"
    ).id


RUTAS = {
    "usuarios/<int:usuario_id>/": _ajeno_usuario,
    "roles/<int:rol_id>/": _ajeno_rol,
    "catalogo/productos/<int:producto_id>/": _ajeno_producto,
    "inventario/ajustes/<int:ajuste_id>/": _ajeno_ajuste,
    "compras/<int:compra_id>/": _ajeno_compra,
    "produccion/<int:op_id>/": _ajeno_op,
    "ventas/pedidos/<int:pedido_id>/": _ajeno_pedido,
}


def _rutas(resolver=None, prefijo=""):
    for patron in (resolver or get_resolver()).url_patterns:
        ruta = prefijo + str(patron.pattern)
        if isinstance(patron, URLResolver):
            yield from _rutas(patron, ruta)
        elif isinstance(patron, URLPattern):
            yield ruta


def test_todos_los_modelos_de_negocio_filtran_por_empresa():
    modelos = [m for m in apps.get_models() if issubclass(m, TenantModel)]
    assert modelos
    for modelo in modelos:
        with pytest.raises(TenantNoDefinido):
            list(modelo.objects.all())
        with tenant_context(123):
            assert '"empresa_id" = 123' in str(modelo.objects.all().query), modelo


def test_toda_ruta_con_id_esta_cubierta():
    con_id = {r for r in _rutas() if "<int:" in r and not r.startswith(EXCLUIDAS)}
    assert con_id == set(RUTAS)


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", sorted(RUTAS))
def test_un_id_de_otra_empresa_da_404(client, crear_empresa, ruta):
    propia, otra = crear_empresa(), crear_empresa(ruc="20100047218")
    for f in CATALOGO:  # todo habilitado: el 404 no debe confundirse con un 403
        PlanFuncionalidad.objects.create(plan=propia.plan, funcionalidad_id=f)
    lucia = asignar_rol(Usuario.objects.create_user("l@a.pe", "x", empresa=propia))
    client.force_login(lucia, BACKEND)
    ajeno = RUTAS[ruta](otra)
    url = "/" + ruta.split("<")[0] + f"{ajeno}/"
    assert client.get(url).status_code == 404
