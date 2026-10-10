"""T6 a T8: tokens de API (RF-TEN-43, 45 a 47, 54; RNF-TEN-02)."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from shared.domain.tenant import tenant_context
from tenancy.application.tokens import CrearTokenApi, DesactivarUsuarioTecnico, RevocarTokenApi
from tenancy.domain.errores import SinApiIntegracion
from tenancy.domain.tokens import hash_token
from tenancy.infrastructure.contenedor import actor_de, caso_de_tokens, plataforma
from tenancy.infrastructure.models import ApiToken, AuditoriaAcceso, Rol, Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
HOY = date.today()


@pytest.fixture
def lucia(crear_empresa):
    empresa = crear_empresa()
    empresa.plan.es_plan_prueba = True
    empresa.plan.save()
    return asignar_rol(Usuario.objects.create_user("lucia@andina.pe", "x", empresa=empresa))


def crear_token(lucia, nombre="n8n-stock"):
    almacen = Rol.all_tenants.get(empresa_id=lucia.empresa_id, nombre="Almacén").id
    return caso_de_tokens(CrearTokenApi).ejecutar(
        actor_de(lucia, HOY), nombre, "n8n", [almacen], HOY
    )


def test_el_modelo_no_guarda_el_token_en_claro_y_el_hash_es_unico(lucia):
    token = crear_token(lucia)
    fila = ApiToken.all_tenants.get()
    assert fila.token_hash == hash_token(token) and fila.prefijo == token[:8]
    assert token not in str(list(ApiToken.all_tenants.values()))
    assert {f.name for f in ApiToken._meta.fields}.isdisjoint({"token", "clave", "secreto"})
    with pytest.raises(IntegrityError), transaction.atomic():
        ApiToken.all_tenants.create(
            empresa_id=fila.empresa_id,
            usuario=fila.usuario,
            nombre="x",
            token_hash=fila.token_hash,
            prefijo="x",
            creado_por=lucia,
        )


def test_crea_el_usuario_tecnico_una_vez_y_audita(lucia):
    crear_token(lucia, "n8n-stock")
    crear_token(lucia, "n8n-ventas")
    tecnico = Usuario.objects.get(es_tecnico=True)
    assert tecnico.nombre == "n8n" and not tecnico.has_usable_password()
    with tenant_context(lucia.empresa_id):
        assert tecnico.tokens.count() == 2
        assert AuditoriaAcceso.objects.filter(entidad="TOKEN_API", accion="CREAR").count() == 2


def test_sin_api_habilitada_no_se_crean_tokens(lucia):
    plataforma().quitar(lucia.empresa_id, ["transversal.api"], "x", None, None, HOY, True)
    lucia_actor = actor_de(lucia, HOY)
    assert "api.token.gestionar" not in lucia_actor.permisos
    caso = caso_de_tokens(CrearTokenApi)
    with pytest.raises(SinApiIntegracion, match="Tu plan no incluye la API de integración"):
        caso.ejecutar.__wrapped__(caso, lucia_actor, "x", "n8n", [], HOY)


def test_revocar_y_desactivar_al_tecnico(lucia):
    crear_token(lucia, "a")
    crear_token(lucia, "b")
    a, b = ApiToken.all_tenants.order_by("id")
    caso_de_tokens(RevocarTokenApi).ejecutar(actor_de(lucia, HOY), a.id)
    a.refresh_from_db()
    assert a.revocado_en is not None
    caso_de_tokens(DesactivarUsuarioTecnico).ejecutar(actor_de(lucia, HOY), b.usuario_id)
    b.refresh_from_db()
    assert b.revocado_en is not None and not b.usuario.is_active
    with tenant_context(lucia.empresa_id):
        acciones = set(AuditoriaAcceso.objects.values_list("entidad", "accion"))
    assert {("TOKEN_API", "REVOCAR"), ("USUARIO", "DESACTIVAR")} <= acciones
