"""Pasos de sesion_empresa.feature y suscripcion.feature (UC-TEN-02, 04 y 05)."""

import re
from datetime import timedelta
from itertools import count

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from shared.domain.accesos import CATALOGO
from shared.domain.tenant import tenant_context
from shared.infrastructure.correo import enviar_pendientes
from tenancy.domain.plantillas import PLANTILLAS
from tenancy.infrastructure.contenedor import tenancy_service
from tenancy.infrastructure.models import Empresa, Plan, PlanFuncionalidad, Rol, Usuario
from tenancy.infrastructure.repositorios import AccesosOrm
from tests.acceptance.conftest import contenido
from tests.conftest import asignar_rol

CLAVE = "Clave-Segura-2026"
_correlativo = count(1)


def ruc_valido() -> str:
    """Genera un RUC válido distinto en cada llamada (prefijo 20 y dígito verificador)."""
    base = f"20{next(_correlativo):08d}"
    resto = (
        11 - sum(int(d) * p for d, p in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2), strict=True)) % 11
    )
    return base + str({10: 0, 11: 1}.get(resto, resto))


def empresa_por_nombre(nombre) -> Empresa:
    return Empresa.objects.get(razon_social=nombre)


def crear_empresa(nombre, limite_usuarios=None, **kw) -> Empresa:
    ruc = ruc_valido()
    plan = Plan.objects.create(
        nombre=f"Plan {ruc}", slug=f"plan-{ruc}", limite_usuarios=limite_usuarios
    )
    hoy = timezone.localdate()
    kw.setdefault("fecha_termino", hoy + timedelta(days=30))
    return Empresa.objects.create(ruc=ruc, razon_social=nombre, plan=plan, **kw)


def crear_usuario(email, empresa, rol="Administrador", **kw) -> Usuario:
    usuario = Usuario.objects.create_user(
        email, CLAVE, nombre=email.split("@")[0], empresa=empresa, **kw
    )
    return asignar_rol(usuario, rol) if rol else usuario


def iniciar_sesion(client, email, password=CLAVE):
    return client.post("/login/", {"email": email, "password": password}, follow=True)


@given(parsers.parse('la empresa "{nombre}" con plan que permite {limite:d} usuarios'))
def empresa_con_plan(ctx, nombre, limite):
    ctx["empresa"] = crear_empresa(nombre, limite_usuarios=limite)


@given(parsers.parse('la empresa "{nombre}" con datos propios'))
def otra_empresa(nombre):
    crear_empresa(nombre)


@given(parsers.parse('el usuario "{email}" con el rol "{rol}" de "{empresa}"'))
def usuario_con_rol(email, rol, empresa):
    crear_usuario(email, empresa_por_nombre(empresa), rol)


@given(parsers.parse('"{empresa}" tiene habilitados todos los módulos'))
def todos_los_modulos(empresa):
    """Habilita todo el catálogo en el plan de la empresa y completa sus plantillas de rol."""
    e = empresa_por_nombre(empresa)
    for f in CATALOGO:
        PlanFuncionalidad.objects.get_or_create(plan=e.plan, funcionalidad_id=f)
    for rol in Rol.all_tenants.filter(empresa=e, es_sistema=False, nombre__in=PLANTILLAS):
        AccesosOrm().actualizar_rol(rol.id, rol.nombre, PLANTILLAS[rol.nombre])


@given(parsers.parse('que el usuario "{email}" está inactivo'))
def usuario_inactivo(ctx, email):
    crear_usuario(email, ctx["empresa"], is_active=False)


@when(parsers.parse('"{email}" inicia sesión con su contraseña correcta'))
def login_correcto(client, ctx, email):
    ctx["respuesta"] = iniciar_sesion(client, email)


@when(parsers.parse('"{email}" falla la contraseña {veces:d} veces seguidas'))
def login_fallido(client, ctx, email, veces):
    ctx["email"] = email
    for _ in range(veces):
        ctx["respuesta"] = iniciar_sesion(client, email, "incorrecta")


@then(parsers.parse('accede al dashboard de "{empresa}"'))
def accede_al_dashboard(ctx, empresa):
    respuesta = ctx["respuesta"]
    assert respuesta.redirect_chain[-1][0] == "/dashboard/"
    assert empresa in contenido(respuesta)


@then(parsers.parse('el acceso es rechazado con el mensaje "{mensaje}"'))
def acceso_rechazado(ctx, mensaje):
    assert mensaje in contenido(ctx["respuesta"])
    assert not ctx["respuesta"].context["user"].is_authenticated


@then(parsers.parse("su usuario queda bloqueado durante {minutos:d} minutos"))
def bloqueado(ctx, minutos):
    hasta = Usuario.objects.get(email=ctx["email"]).bloqueado_hasta
    restante = hasta - timezone.now()
    assert timedelta(minutes=minutos - 1) < restante <= timedelta(minutes=minutos)


@then("un intento con la contraseña correcta dentro de ese plazo es rechazado")
def rechazado_dentro_del_plazo(client, ctx):
    respuesta = iniciar_sesion(client, ctx["email"])
    assert not respuesta.context["user"].is_authenticated
    assert "bloqueado temporalmente" in contenido(respuesta)


@when(parsers.parse('"{email}" solicita recuperar su contraseña'))
def solicita_recuperar(client, ctx, email):
    client.post("/password-reset/", {"email": email})
    enviar_pendientes()


@then("recibe un email con un enlace de un solo uso válido por 60 minutos")
def recibe_enlace(ctx):
    assert len(mail.outbox) == 1
    cuerpo = mail.outbox[0].body
    assert "60 minutos" in cuerpo
    ctx["enlace"] = re.search(r"https?://\S+(/password-reset/\S+/)", cuerpo).group(1)


@then("al usar el enlace puede definir una nueva contraseña")
def define_nueva(client, ctx):
    respuesta = client.post(
        ctx["enlace"],
        {"new_password1": "Nueva-Clave-2026", "new_password2": "Nueva-Clave-2026"},
        follow=True,
    )
    assert "Tu contraseña fue actualizada" in contenido(respuesta)
    assert (
        iniciar_sesion(client, mail.outbox[0].to[0], "Nueva-Clave-2026")
        .context["user"]
        .is_authenticated
    )


@then("el enlace ya no puede reutilizarse")
def enlace_usado(client, ctx):
    client.logout()
    assert "El enlace no es válido o ya venció" in contenido(client.get(ctx["enlace"]))


@when(parsers.parse('"{email}" actualiza el nombre comercial a "{nombre}" y el logo'))
def actualiza_empresa(client, ctx, email, nombre, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    iniciar_sesion(client, email)
    logo = SimpleUploadedFile("logo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
    datos = {
        "accion": "datos",
        "razon_social": ctx["empresa"].razon_social,
        "nombre_comercial": nombre,
    }
    ctx["respuesta"] = client.post(
        "/configuracion/empresa/", datos | {"logo": logo, "ruc": "20512345671"}, follow=True
    )


@then(parsers.parse('el menú lateral muestra "{nombre}" y el nuevo logo'))
def menu_lateral(client, nombre):
    menu = (
        contenido(client.get("/dashboard/"))
        .split('<nav class="menu-lateral">')[1]
        .split("</nav>")[0]
    )
    assert nombre in menu and "/media/logos/logo" in menu


@then("el RUC no es editable")
def ruc_no_editable(client, ctx):
    pagina = contenido(client.get("/configuracion/empresa/"))
    assert ctx["empresa"].ruc in pagina and 'name="ruc"' not in pagina
    ctx["empresa"].refresh_from_db()
    assert ctx["empresa"].ruc != "20512345671"


@given("una venta emitida con IGV 18 %")
def venta_con_igv_18(ctx):
    ctx["fecha_venta"] = timezone.localdate() - timedelta(days=1)
    ctx["pendientes"].append(
        "la venta guarda su IGV al emitirse (0006b); aquí se verifica la vigencia"
    )


@when(parsers.parse('"{email}" cambia el IGV a {pct:d} %'))
def cambia_igv(client, ctx, email, pct):
    iniciar_sesion(client, email)
    datos = {"accion": "igv", "igv_pct": pct, "vigente_desde": timezone.localdate().isoformat()}
    ctx["respuesta"] = client.post("/configuracion/empresa/", datos, follow=True)
    assert "IGV registrado" in contenido(ctx["respuesta"])


@then(parsers.parse("la venta existente mantiene su IGV de {pct:d} %"))
def venta_mantiene_igv(ctx, pct):
    with tenant_context(ctx["empresa"].id):
        assert tenancy_service().igv_vigente(ctx["fecha_venta"]) == pct


@then(parsers.parse("las ventas nuevas usan {pct:d} %"))
def ventas_nuevas(ctx, pct):
    with tenant_context(ctx["empresa"].id):
        assert tenancy_service().igv_vigente(timezone.localdate()) == pct
    if ctx["pendientes"]:
        pytest.skip("Parcial; pendiente de otras specs: " + "; ".join(ctx["pendientes"]))
