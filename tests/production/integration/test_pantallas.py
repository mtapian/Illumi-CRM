"""0005a, T8: pantallas de OP (RF-PRD-34, 36 a 39, 41, 44 a 46, 48)."""

from decimal import Decimal as D

import pytest

from catalog.infrastructure.models import Producto, Unidad
from production.infrastructure.models import OrdenProduccion
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import Rol, RolPermiso, Usuario
from tests.conftest import asignar_rol
from tests.production.usecases.test_finalizar import ej  # noqa: F401

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


@pytest.fixture
def web(client, ej, empresa_produccion):  # noqa: F811
    empresa, actor = empresa_produccion
    client.force_login(Usuario.objects.get(pk=actor.usuario_id), BACKEND)
    return client, ej, empresa


def test_crear_editar_y_finalizar_con_dos_salidas_desde_la_pantalla(web):
    """RF-PRD-36 a 41, RF-PRD-48 (listado) y enmienda 1 (RF-PRD-49 a 52; RF-PRD-53, costos
    por salida): el indirecto se reparte por producida × factor; un lote por producto."""
    client, (actor, almacen, ids), empresa = web
    with tenant_context(empresa.id):
        apa = Producto.objects.create(
            sku="GRA-APA",
            nombre="APA a granel",
            unidad=Unidad.objects.get(abreviatura="L"),
            se_compra=False,
            se_fabrica=True,
        ).id
    cabecera = {
        "fecha_programada": "2026-10-12",
        "almacen_origen": almacen,
        "almacen_destino": almacen,
        "responsable": actor.usuario_id,
        "comentario": "Bar Central",
    }
    salidas = [(ids["GRA-IPA"], "500", ""), (apa, "100", "")]
    r = client.post(
        "/produccion/nueva/",
        _codificar(cabecera | {"usar_receta": "on"}, salidas, []),
        content_type="application/x-www-form-urlencoded",
    )
    with tenant_context(empresa.id):
        op = OrdenProduccion.objects.get()
        filas = [
            (c.producto_id, str(c.por_consumir), str(c.salida.producto_id))
            for c in op.componentes.select_related("salida").order_by("id")
        ]
    assert r.url == f"/produccion/{op.id}/"
    ficha = client.get(r.url).content.decode()
    assert "OP-000001" in ficha and "Disponible" in ficha and "Pasar a en proceso" in ficha
    assert "Productos de salida" in ficha and "Guardar como receta del producto" in ficha
    assert {f[2] for f in filas} == {str(ids["GRA-IPA"])}  # la receta del IPA, asignada a él
    post = cabecera | {"accion": "en_proceso"}
    client.post(
        r.url, _codificar(post, salidas, filas), content_type="application/x-www-form-urlencoded"
    )
    with tenant_context(empresa.id):
        op.refresh_from_db()
    assert op.estado == "EN_PROCESO"
    ficha = client.get(r.url).content.decode()
    assert 'id="finalizar-op"' in ficha and "GRA-IPA-0001" in ficha and "GRA-APA-0001" in ficha
    fin = {
        "accion": "finalizar",
        f"producida_{ids['GRA-IPA']}": "425",
        f"producida_{apa}": "75",
        "fecha_fin": "2026-10-12",
        f"consumido_{ids['INS-MALTA']}_{ids['GRA-IPA']}": "100",
        "costo_indirecto": "52",
    }
    client.post(r.url, fin)
    with tenant_context(empresa.id):
        op.refresh_from_db()
        costos = {
            x.producto_id: (x.costo_total, x.costo_unitario, x.lote_codigo)
            for x in op.salidas.all()
        }
    assert op.estado == "FINALIZADA"
    # 790 de componentes del IPA + 52 × 425/500 = 834.20; el APA: 52 × 75/500 = 7.80
    assert costos == {
        ids["GRA-IPA"]: (D("834.20"), D("1.962824"), "GRA-IPA-0001"),
        apa: (D("7.80"), D("0.104000"), "GRA-APA-0001"),
    }
    ficha = client.get(r.url).content.decode()
    assert "Costos" in ficha and "S/ 1.962824" in ficha and "Movimientos de kardex" in ficha
    listado = client.get("/produccion/", {"estado": "FINALIZADA"}).content.decode()
    assert "OP-000001" in listado and "GRA-APA" in listado
    assert "OP-000001" not in client.get("/produccion/", {"estado": "CREADA"}).content.decode()
    kardex = client.get("/inventario/kardex/", {"producto": ids["GRA-IPA"]}).content.decode()
    assert f'href="/produccion/{op.id}/"' in kardex


def _codificar(cabecera, salidas, componentes):
    from urllib.parse import urlencode

    pares = list(cabecera.items())
    for p, q, f in salidas:
        pares += [("salida_producto", p), ("salida_cantidad", q), ("salida_factor", f)]
    for c, q, para in componentes:
        pares += [("componente", c), ("por_consumir", q), ("costo", ""), ("para", para)]
    return urlencode(pares)


def test_costos_ocultos_sin_permiso_de_costos(web):
    """RF-PRD-34; RF-TEN-51."""
    client, (actor, almacen, ids), empresa = web
    from tests.production.usecases.test_finalizar import finalizar, op_en_proceso

    with tenant_context(empresa.id):
        op_id = op_en_proceso((actor, almacen, ids), "GRA-IPA", "500")
        finalizar((actor, almacen, ids), op_id, "425")
        rol = Rol.objects.create(nombre="Sin costos")
        for p in ("produccion.op.ver", "produccion.reporte.ver"):
            RolPermiso.objects.create(rol=rol, permiso_id=p)
    ana = Usuario.objects.create_user("ana@andina.pe", "x", empresa=empresa)
    asignar_rol(ana, "Sin costos")
    client.force_login(ana, BACKEND)
    ficha = client.get(f"/produccion/{op_id}/").content.decode()
    assert "Tu rol no puede ver costos" in ficha and "S/ 2.000000" not in ficha
