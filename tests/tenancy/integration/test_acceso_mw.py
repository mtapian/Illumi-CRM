"""T8 y T9: el Actor se recalcula en cada request (RF-TEN-40 a 42, 49)."""

from datetime import date

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from shared.domain.errores import NoEncontrado
from tenancy.application.usuarios import EditarUsuario
from tenancy.infrastructure.contenedor import actor_de, caso_de_uso, plataforma
from tenancy.infrastructure.models import PlanFuncionalidad, Usuario
from tenancy.interfaces.acceso import AccesoMiddleware, requiere
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
HOY = date.today()


@pytest.fixture
def rosa(crear_empresa):
    empresa = crear_empresa()
    for f in ("catalogo.productos", "inventario.stock", "inventario.ajustes"):
        PlanFuncionalidad.objects.create(plan=empresa.plan, funcionalidad_id=f)
    return asignar_rol(
        Usuario.objects.create_user("rosa@andina.pe", "x", empresa=empresa), "Almacén"
    )


def test_quitar_la_funcionalidad_rechaza_la_siguiente_accion_sin_guardar(rosa):
    guardadas = []

    @requiere("inventario.ajuste.registrar")
    def registrar_ajuste(request):
        guardadas.append(1)
        return HttpResponse("ok")

    def pedir():
        request = RequestFactory().post("/inventario/ajustes/")
        request.user = rosa
        middleware = AccesoMiddleware(registrar_ajuste)
        try:
            return middleware(request)
        except Exception as e:  # el handler de Django llama a process_exception
            return middleware.process_exception(request, e)

    assert pedir().status_code == 200
    plataforma().quitar(rosa.empresa_id, ["inventario.ajustes"], "Pedido", None, None, HOY, True)
    respuesta = pedir()
    assert respuesta.status_code == 403
    assert "Esta funcionalidad ya no está disponible en tu plan" in respuesta.content.decode()
    assert guardadas == [1]


def test_un_usuario_sin_permisos_efectivos_ve_sin_modulos(client, crear_empresa):
    usuario = Usuario.objects.create_user("pedro@andina.pe", "x", empresa=crear_empresa())
    client.force_login(usuario, "tenancy.infrastructure.auth_backend.EmailBackend")
    assert "No tienes módulos asignados" in client.get("/dashboard/").content.decode()
    assert client.post("/logout/").status_code == 302


def test_un_id_de_otra_empresa_da_404(client, crear_empresa):
    lucia = asignar_rol(Usuario.objects.create_user("l@a.pe", "x", empresa=crear_empresa()))
    otra = crear_empresa(ruc="20100047218")
    ajeno = Usuario.objects.create_user("x@b.pe", "x", empresa=otra)
    client.force_login(lucia, "tenancy.infrastructure.auth_backend.EmailBackend")
    assert client.get(f"/usuarios/{ajeno.id}/").status_code == 404
    with pytest.raises(NoEncontrado):
        caso_de_uso(EditarUsuario).ejecutar(actor_de(lucia, HOY), ajeno.id, "x")
