"""T11: aislamiento entre empresas (RF-TEN-52, RNF-TEN-05; constitución, art. 3.2).

1. Todo modelo de negocio (`TenantModel`) se consulta filtrado por la empresa actual.
2. Toda ruta de empresa con un identificador responde 404 con un id de otra empresa.
   Cada ruta nueva con `<int:…>` debe agregarse a `RUTAS`: si no, el test falla.
"""

import pytest
from django.apps import apps
from django.urls import URLPattern, URLResolver, get_resolver

from shared.domain.tenant import TenantNoDefinido, tenant_context
from shared.infrastructure.tenant_models import TenantModel
from tenancy.infrastructure.models import Rol, Usuario
from tests.conftest import asignar_rol

BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"
EXCLUIDAS = ("plataforma/", "password-reset/")  # datos de plataforma (art. 3.1) y token


def _ajeno_usuario(otra):
    return Usuario.objects.create_user("x@brew.pe", "x", empresa=otra).id


def _ajeno_rol(otra):
    return Rol.all_tenants.create(empresa=otra, nombre="Ajeno").id


# ruta → función que crea un registro de la otra empresa y devuelve su id
RUTAS = {
    "usuarios/<int:usuario_id>/": _ajeno_usuario,
    "roles/<int:rol_id>/": _ajeno_rol,
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
    lucia = asignar_rol(Usuario.objects.create_user("l@a.pe", "x", empresa=propia))
    client.force_login(lucia, BACKEND)
    ajeno = RUTAS[ruta](otra)
    url = "/" + ruta.split("<")[0] + f"{ajeno}/"
    assert client.get(url).status_code == 404
