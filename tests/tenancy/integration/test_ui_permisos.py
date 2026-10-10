"""T10 y T20: menú y botones según permisos; costos ocultos (RF-TEN-50, 51)."""

import pytest

from shared.interfaces.costos import sin_costos
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"


def menu(client):
    pagina = client.get("/dashboard/").content.decode()
    return pagina.split('<nav class="menu-lateral">')[1].split("</nav>")[0], pagina


def test_el_menu_y_los_botones_dependen_de_los_permisos(client, crear_empresa):
    empresa = crear_empresa()
    lucia = asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))
    ana = asignar_rol(Usuario.objects.create_user("ana@andina.pe", "x", empresa=empresa), "Ventas")
    client.force_login(lucia, BACKEND)
    nav, pagina = menu(client)
    assert "/usuarios/" in nav and "/roles/" in nav and "/configuracion/empresa/" in nav
    client.force_login(ana, BACKEND)
    nav, pagina = menu(client)
    assert "/usuarios/" not in nav and "/roles/" not in nav
    assert "/configuracion/empresa/" not in pagina  # tampoco el enlace de primeros pasos
    assert client.get("/usuarios/").status_code == 403


def test_el_helper_omite_los_costos_sin_permiso():
    filas = [{"producto": "Stout", "cantidad": 10, "costo_promedio": 4, "valorizacion": 40}]
    assert sin_costos(filas, {"inventario.costo.ver"}) == filas
    assert sin_costos(filas, set()) == [{"producto": "Stout", "cantidad": 10}]
    columnas = ["producto", "cantidad", "costo_promedio", "valorizacion"]
    assert sin_costos(columnas, set()) == ["producto", "cantidad"]
