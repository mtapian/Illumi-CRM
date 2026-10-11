"""Pasos de suscripcion.feature (UC-TEN-05)."""

from datetime import timedelta

from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import Empresa, Usuario
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_sesion import crear_empresa, crear_usuario, iniciar_sesion


def empresa_en_prueba(ctx, nombre, fecha_termino):
    ctx["empresa"] = crear_empresa(nombre, estado=Estado.TRIAL, fecha_termino=fecha_termino)
    ctx["email"] = "ana@andina.pe"
    crear_usuario(ctx["email"], ctx["empresa"])


@given(parsers.parse('que la prueba de "{nombre}" vence en {dias:d} días'))
def prueba_vence_en(ctx, nombre, dias):
    empresa_en_prueba(ctx, nombre, timezone.localdate() + timedelta(days=dias))


@given(parsers.parse('que la prueba de "{nombre}" venció ayer'))
def prueba_vencida(ctx, nombre):
    empresa_en_prueba(ctx, nombre, timezone.localdate() - timedelta(days=1))


@given(parsers.parse('que "{email}" tiene una sesión abierta'))
def sesion_abierta(client, ctx, email):
    empresa_en_prueba(ctx, "Cervecería Andina", timezone.localdate() + timedelta(days=30))
    assert iniciar_sesion(client, email).context["user"].is_authenticated


@when("un usuario de la empresa navega por el sistema")
def navega(client, ctx):
    iniciar_sesion(client, ctx["email"])
    ctx["respuesta"] = client.get("/dashboard/")


@when("un usuario de la empresa intenta abrir el módulo de ventas")
def abre_ventas(client, ctx):
    iniciar_sesion(client, ctx["email"])
    ctx["respuesta"] = client.get("/ventas/")


@when(parsers.parse('el super admin suspende "{nombre}"'))
def super_admin_suspende(nombre):
    # La acción completa (con motivo y registro de actividad) llega con 0001b.
    Empresa.objects.filter(razon_social=nombre).update(estado=Estado.SUSPENDIDA)


@when(parsers.parse('"{email}" hace su siguiente acción'))
def siguiente_accion(client, ctx, email):
    ctx["respuesta"] = client.get("/dashboard/")


@then(parsers.parse('ve un banner "{texto}"'))
def ve_banner(ctx, texto):
    assert texto in contenido(ctx["respuesta"])


@then("es redirigido a la página de suscripción")
@then("es redirigida a la página de suscripción")
def redirigido_a_suscripcion(ctx):
    assert ctx["respuesta"].status_code == 302
    assert ctx["respuesta"]["Location"] == "/suscripcion/"


@then("solo puede ver la suscripción o cerrar sesión")
def solo_suscripcion(client):
    assert client.get("/suscripcion/").status_code == 200
    assert client.get("/dashboard/")["Location"] == "/suscripcion/"
    assert client.post("/logout/")["Location"] == "/login/"


@then("los datos de la empresa se conservan")
def datos_conservados(ctx):
    assert Empresa.objects.filter(pk=ctx["empresa"].pk).exists()
    assert Usuario.objects.filter(email=ctx["email"]).exists()
