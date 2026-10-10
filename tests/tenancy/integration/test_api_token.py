"""T9: llamadas con token de API (RF-TEN-46, 48, 54)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from shared.domain.tenant import TenantNoDefinido, empresa_actual
from tenancy.application.tokens import CrearTokenApi
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.contenedor import actor_de, caso_de_tokens, plataforma
from tenancy.infrastructure.models import ApiToken, Empresa, Rol, Usuario
from tests.conftest import asignar_rol

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.api_urls")]
HOY = timezone.localdate()


@pytest.fixture
def token(crear_empresa):
    empresa = crear_empresa()
    empresa.plan.es_plan_prueba = True
    empresa.plan.save()
    lucia = asignar_rol(Usuario.objects.create_user("l@a.pe", "x", empresa=empresa))
    otra = crear_empresa(ruc="20100047218")
    asignar_rol(Usuario.objects.create_user("x@b.pe", "x", empresa=otra))
    almacen = Rol.all_tenants.get(empresa=empresa, nombre="Almacén").id
    return caso_de_tokens(CrearTokenApi).ejecutar(
        actor_de(lucia, HOY), "n8n", "n8n", [almacen], HOY
    )


def llamar(client, token, url="/api/prueba/"):
    return client.get(url, HTTP_AUTHORIZATION=f"Token {token}")


def test_solo_datos_de_su_empresa_paginados_y_sin_fugar_la_empresa(client, token):
    respuesta = llamar(client, token)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert {"count", "next", "results"} <= set(datos)
    empresa = ApiToken.all_tenants.get().empresa_id
    assert datos["count"] == 5 and {r["empresa_id"] for r in datos["results"]} == {empresa}
    assert ApiToken.all_tenants.get().ultimo_uso_en is not None
    with pytest.raises(TenantNoDefinido):
        empresa_actual()


def test_sin_token_o_token_falso_da_401(client, token):
    assert client.get("/api/prueba/").status_code == 401
    assert llamar(client, "falso").status_code == 401


def test_sin_el_permiso_del_tecnico_da_403(client, token):
    assert llamar(client, token, "/api/prueba-sin-permiso/").status_code == 403


@pytest.mark.parametrize(
    "cambio", [{"estado": Estado.SUSPENDIDA}, {"fecha_termino": HOY - timedelta(days=1)}]
)
def test_empresa_suspendida_o_vencida_da_401(client, token, cambio):
    Empresa.objects.filter(pk=ApiToken.all_tenants.get().empresa_id).update(**cambio)
    assert llamar(client, token).status_code == 401


def test_sin_api_habilitada_da_403(client, token):
    empresa = ApiToken.all_tenants.get().empresa_id
    plataforma().quitar(empresa, ["transversal.api"], "x", None, None, HOY, True)
    assert llamar(client, token).status_code == 403
