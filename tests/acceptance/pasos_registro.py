"""Pasos de registro_empresa.feature (UC-TEN-01)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from catalog.infrastructure.models import Unidad
from tenancy.application.sembradores import RegistroSembradores
from tenancy.infrastructure.models import Empresa, Plan, Usuario, UsuarioRol
from tests.acceptance.conftest import contenido, no_hay_empresas_ni_usuarios_de_empresa

DATOS_VALIDOS = {
    "ruc": "20601234565",
    "razon_social": "Cervecería Andina S.A.C.",
    "nombre_comercial": "",
    "nombre": "Lucía Torres",
    "email": "lucia@andina.pe",
    "password": "Clave-Segura-2026",
}


def registrarse(client, ctx, **cambios):
    ctx["respuesta"] = client.post("/registro/", DATOS_VALIDOS | cambios, follow=True)


@given(parsers.parse("que la plataforma tiene configurados {dias:d} días de prueba"))
def dias_de_prueba(ctx, dias):
    ctx["dias_prueba"] = dias


@given(parsers.parse('que existe el plan de prueba "{nombre}"'))
def plan_de_prueba(ctx, nombre):
    Plan.objects.create(
        nombre=nombre, slug=nombre.lower(), es_plan_prueba=True, dias_prueba=ctx["dias_prueba"]
    )


@given(parsers.parse('que existe una empresa con RUC "{ruc}"'))
def empresa_existente(client, ctx, ruc):
    client.post("/registro/", DATOS_VALIDOS | {"ruc": ruc, "email": "otro@andina.pe"})
    client.logout()


@given(parsers.parse('que existe un usuario con email "{email}"'))
def usuario_existente(email):
    Usuario.objects.create_user(email, "Clave-Segura-2026", nombre="Existente")


@given("que la creación del almacén inicial va a fallar")
def almacen_falla(monkeypatch):
    def falla(empresa, admin, hoy):
        raise RuntimeError("no se pudo crear el almacén Principal")

    registro = RegistroSembradores()
    registro.registrar(falla)
    monkeypatch.setattr("tenancy.infrastructure.contenedor.sembradores", registro)


@when("me registro con:")
def registro_con_tabla(client, ctx, datatable):
    registrarse(client, ctx, **{fila[0]: fila[1] for fila in datatable[1:]})


@when(parsers.parse('me registro con el RUC "{ruc}"'))
def registro_con_ruc(client, ctx, ruc):
    registrarse(client, ctx, ruc=ruc, email="nuevo@andina.pe")


@when(parsers.parse('me registro con el email "{email}"'))
def registro_con_email(client, ctx, email):
    registrarse(client, ctx, email=email)


@when("me registro con datos válidos")
def registro_valido(client, ctx):
    registrarse(client, ctx)


@then(parsers.parse('se crea la empresa "{razon_social}" en estado "{estado}"'))
def empresa_creada(ctx, razon_social, estado):
    ctx["empresa"] = Empresa.objects.get(razon_social=razon_social)
    assert ctx["empresa"].estado == estado.upper()


@then(parsers.parse("la prueba termina {dias:d} días después de hoy"))
def fin_de_prueba(ctx, dias):
    assert ctx["empresa"].fecha_termino == timezone.localdate() + timedelta(days=dias)


@then(parsers.parse('"{email}" es administrador activo de esa empresa'))
def administrador_activo(ctx, email):
    usuario = Usuario.objects.get(email=email)
    assert usuario.is_active and usuario.empresa_id == ctx["empresa"].id
    roles = UsuarioRol.objects.filter(usuario=usuario).values_list("rol__nombre", flat=True)
    assert list(roles) == ["Administrador"]


@then(parsers.parse('la empresa tiene el almacén "{nombre}"'))
def tiene_almacen(ctx, nombre):
    ctx["pendientes"].append(f'almacén "{nombre}" (lo siembra 0003a)')


@then(parsers.parse('la empresa tiene las unidades de medida iniciales "{unidades}"'))
def tiene_unidades(ctx, unidades):
    filas = Unidad.all_tenants.filter(empresa=ctx["empresa"])
    assert {u.strip() for u in unidades.split(",")} <= set(
        filas.values_list("abreviatura", flat=True)
    )


@then("la empresa tiene las categorías de gasto iniciales")
def tiene_categorias(ctx):
    ctx["pendientes"].append("categorías de gasto (las siembra 0008a)")


@then("quedo autenticado en el dashboard de la empresa")
def autenticado_en_dashboard(ctx):
    respuesta = ctx["respuesta"]
    assert respuesta.redirect_chain[-1][0] == "/dashboard/"
    assert respuesta.context["user"].is_authenticated
    assert "Primeros pasos" in contenido(respuesta)
    if ctx["pendientes"]:
        pytest.skip("Parcial; pendiente de otras specs: " + "; ".join(ctx["pendientes"]))


@then(parsers.parse('el registro es rechazado con el mensaje "{mensaje}"'))
def registro_rechazado(ctx, mensaje):
    assert mensaje in contenido(ctx["respuesta"])


@then("no se crea ninguna empresa ni usuario")
def nada_creado():
    assert no_hay_empresas_ni_usuarios_de_empresa()


@then("no se crea ninguna empresa")
def ninguna_empresa():
    assert not Empresa.objects.exists()


@then("veo un mensaje de error genérico para reintentar")
def error_generico(ctx):
    assert "No pudimos completar el registro. Inténtalo de nuevo." in contenido(ctx["respuesta"])
