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
    "url", ["/plataforma/empresas/", "/plataforma/planes/", "/plataforma/empresas/1/modulos/"]
)
def test_un_usuario_de_empresa_recibe_403(client, crear_empresa, url):
    usuario = asignar_rol(
        Usuario.objects.create_user("ana@andina.pe", "x", empresa=crear_empresa())
    )
    client.force_login(usuario, BACKEND)
    assert client.get(url).status_code == 403
