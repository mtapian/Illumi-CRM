"""0005a, T8: pantallas de OP (RF-PRD-34, 36 a 39, 41, 44 a 46, 48)."""

from decimal import Decimal as D

import pytest

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


def test_crear_editar_y_finalizar_desde_la_pantalla(web):
    """RF-PRD-36 a 41 desde la ficha; RF-PRD-48: listado con filtro por estado."""
    client, (actor, almacen, ids), empresa = web
    datos = {
        "producto": ids["GRA-IPA"],
        "cantidad": "500",
        "fecha_programada": "2026-10-12",
        "almacen_origen": almacen,
        "almacen_destino": almacen,
        "responsable": actor.usuario_id,
        "comentario": "Bar Central",
        "usar_receta": "on",
    }
    r = client.post("/produccion/nueva/", datos)
    with tenant_context(empresa.id):
        op = OrdenProduccion.objects.get()
    assert r.url == f"/produccion/{op.id}/"
    ficha = client.get(r.url).content.decode()
    assert "OP-000001" in ficha and "Disponible" in ficha and "Pasar a en proceso" in ficha
    assert "Guardar como receta del producto" in ficha
    with tenant_context(empresa.id):
        filas = [(c.producto_id, str(c.por_consumir)) for c in op.componentes.order_by("id")]
    post = {k: v for k, v in datos.items() if k != "usar_receta"} | {"accion": "en_proceso"}
    client.post(r.url, _codificar(post, filas), content_type="application/x-www-form-urlencoded")
    with tenant_context(empresa.id):
        op.refresh_from_db()
    assert op.estado == "EN_PROCESO"
    ficha = client.get(r.url).content.decode()
    assert 'id="finalizar-op"' in ficha and "GRA-IPA-0001" in ficha  # lote sugerido
    fin = {
        "accion": "finalizar",
        "producida": "425",
        "fecha_fin": "2026-10-12",
        f"consumido_{ids['INS-MALTA']}": "102",
        "costo_indirecto": "52",
    }
    client.post(r.url, fin)
    with tenant_context(empresa.id):
        op.refresh_from_db()
        assert (op.estado, op.costo_unitario) == ("FINALIZADA", D("2.000000"))
    ficha = client.get(r.url).content.decode()
    assert "Costos" in ficha and "S/ 2.000000" in ficha and "Movimientos de kardex" in ficha
    listado = client.get("/produccion/", {"estado": "FINALIZADA"}).content.decode()
    assert "OP-000001" in listado
    assert "OP-000001" not in client.get("/produccion/", {"estado": "CREADA"}).content.decode()
    kardex = client.get("/inventario/kardex/", {"producto": ids["GRA-IPA"]}).content.decode()
    assert f'href="/produccion/{op.id}/"' in kardex


def _codificar(cabecera, filas):
    from urllib.parse import urlencode

    pares = list(cabecera.items())
    for c, q in filas:
        pares += [("componente", c), ("por_consumir", q), ("costo", "")]
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
