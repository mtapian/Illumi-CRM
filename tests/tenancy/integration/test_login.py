"""T16 y T17: login con mensaje por motivo (RF-TEN-06 a 08)."""

import pytest

from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import Usuario

pytestmark = pytest.mark.django_db
CLAVE = "Clave-Segura-2026"


def login(client, email, password=CLAVE):
    return client.post("/login/", {"email": email, "password": password}, follow=True)


def test_el_super_admin_llega_al_panel_de_plataforma(client):
    Usuario.objects.create_user("admin@illumi.pe", CLAVE, nombre="Admin", is_super=True)
    assert login(client, "admin@illumi.pe").redirect_chain[-1][0] == "/plataforma/"


def test_empresa_suspendida_recibe_el_motivo(client, crear_empresa):
    empresa = crear_empresa(estado=Estado.SUSPENDIDA)
    Usuario.objects.create_user("ana@andina.pe", CLAVE, nombre="Ana", empresa=empresa)
    respuesta = login(client, "ana@andina.pe")
    assert "Tu empresa está suspendida" in respuesta.content.decode()
    assert not respuesta.context["user"].is_authenticated


def test_credenciales_incorrectas_dan_un_mensaje_generico(client, crear_empresa):
    Usuario.objects.create_user("ana@andina.pe", CLAVE, nombre="Ana", empresa=crear_empresa())
    for email, password in [("ana@andina.pe", "mala"), ("nadie@andina.pe", CLAVE)]:
        assert "Email o contraseña incorrectos" in login(client, email, password).content.decode()


def test_el_usuario_tecnico_no_inicia_sesion(client, crear_empresa):
    Usuario.objects.create_user(
        "n8n@andina.pe", CLAVE, nombre="n8n", es_tecnico=True, empresa=crear_empresa()
    )
    assert not login(client, "n8n@andina.pe").context["user"].is_authenticated


def test_un_login_correcto_reinicia_los_intentos(client, crear_empresa):
    u = Usuario.objects.create_user("ana@andina.pe", CLAVE, nombre="Ana", empresa=crear_empresa())
    for _ in range(4):
        login(client, "ana@andina.pe", "mala")
    login(client, "ana@andina.pe")
    u.refresh_from_db()
    assert u.intentos_fallidos == 0 and u.bloqueado_hasta is None
