"""T9: solo el super admin entra a la plataforma; filtra empresas sin elegir una (RF-TEN-24)."""

import pytest

from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


def test_el_super_admin_filtra_empresas_por_estado_y_plan(client, crear_empresa):
    activa = crear_empresa(razon_social="Andina", estado=Estado.ACTIVA)
    crear_empresa(ruc="20100047218", razon_social="Brew Lima", estado=Estado.SUSPENDIDA)
    client.force_login(Usuario.objects.create_user("s@illumi.pe", "x", is_super=True), BACKEND)
    pagina = client.get("/plataforma/empresas/?estado=ACTIVA").content.decode()
    assert "Andina" in pagina and "Brew Lima" not in pagina
    pagina = client.get(f"/plataforma/empresas/?plan={activa.plan_id}").content.decode()
    assert "Andina" in pagina and "Brew Lima" not in pagina


@pytest.mark.parametrize(
    "url",
    [
        "/plataforma/empresas/",
        "/plataforma/planes/",
        "/plataforma/empresas/1/modulos/",
        "/plataforma/tipos-documento/",
    ],
)
def test_un_usuario_de_empresa_recibe_403(client, crear_empresa, url):
    usuario = asignar_rol(
        Usuario.objects.create_user("ana@andina.pe", "x", empresa=crear_empresa())
    )
    client.force_login(usuario, BACKEND)
    assert client.get(url).status_code == 403


def test_maestro_de_tipos_de_documento(client):
    """0006a, RF-VEN-49: listado, alta de un tipo nuevo y abreviatura fija al editar."""
    from tenancy.infrastructure.models import TipoDocumento

    client.force_login(Usuario.objects.create_user("s@illumi.pe", "x", is_super=True), BACKEND)
    pagina = client.get("/plataforma/tipos-documento/").content.decode()
    assert "Carné de extranjería" in pagina and "Dígito verificador del RUC" in pagina
    datos = {"abreviatura": "cdi", "codigo_sunat": "a", "nombre": "Cédula diplomática"}
    datos |= {"exige_numero": "on", "longitud_min": "1", "longitud_max": "15"}
    datos |= {"caracteres": "ALFANUMERICO", "validacion": "NINGUNA", "activo": "on"}
    client.post("/plataforma/tipos-documento/", datos)
    nuevo = TipoDocumento.objects.get(abreviatura="CDI")
    assert nuevo.codigo_sunat == "A"
    formulario = client.get(f"/plataforma/tipos-documento/?editar={nuevo.id}").content.decode()
    assert "readonly" in formulario.split('name="abreviatura"')[1].split(">")[0]
