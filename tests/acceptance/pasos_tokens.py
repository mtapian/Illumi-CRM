"""Pasos de auditoria_accesos.feature y tokens_api.feature (0001d)."""

import re
from datetime import datetime, timedelta

from django.utils import timezone
from pytest_bdd import given, then, when

from tenancy.application.roles import EditarRol
from tenancy.application.tokens import CrearTokenApi
from tenancy.domain.tokens import hash_token
from tenancy.infrastructure.contenedor import caso_de_tokens, caso_de_uso, plataforma
from tenancy.infrastructure.models import (
    ApiToken,
    AuditoriaAcceso,
    Empresa,
    PlanFuncionalidad,
    Rol,
    Usuario,
)
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, hoy, re_, rol_id
from tests.acceptance.pasos_sesion import crear_empresa, empresa_por_nombre
from tests.conftest import asignar_rol

API = "transversal.api"


# --- auditoria_accesos.feature (UC-TEN-10) ---


@given(re_("que {} quitó {} del rol {} el {}", "email", "permiso", "rol", "fecha"))
def quito_permiso(ctx, monkeypatch, email, permiso, rol, fecha):
    rol_ = Rol.all_tenants.get(empresa=ctx["empresa"], nombre=rol)
    permisos = set(rol_.permisos.values_list("permiso", flat=True)) - {permiso}
    momento = timezone.make_aware(datetime.fromisoformat(f"{fecha}T10:00"))
    with monkeypatch.context() as m:
        m.setattr(timezone, "now", lambda: momento)
        caso_de_uso(EditarRol).ejecutar(actor(email), rol_.id, rol, permisos, hoy())
    ctx["permiso"], ctx["fecha"] = permiso, fecha


@when("consulto la auditoría de accesos")
def consulto_auditoria(client, ctx):
    ctx["pagina"] = contenido(como(client, "lucia@andina.pe").get("/auditoria/accesos/"))


@then(
    re_(
        "veo el cambio con autor {}, fecha, rol {}, antes {} y después {}",
        "email",
        "rol",
        "antes",
        "despues",
    )
)
def veo_cambio(ctx, email, rol, antes, despues):
    filas = re.findall(r"<tr>(.*?)</tr>", ctx["pagina"], re.S)
    esperado = f"{ctx['permiso']}: {antes} → {despues}"
    assert any(
        ctx["fecha"] in f and email in f and f"<strong>{rol}</strong>" in f and esperado in f
        for f in filas
    )


# --- tokens_api.feature (UC-TEN-11) ---


@given(re_("la empresa {} con la funcionalidad {} habilitada", "nombre", "funcionalidad"))
def empresa_con_api(ctx, settings, nombre, funcionalidad):
    settings.ROOT_URLCONF = "tests.api_urls"  # incluye una consulta de prueba de la API
    ctx["empresa"] = crear_empresa(nombre)
    for f in (API, "catalogo.productos", "inventario.stock"):
        PlanFuncionalidad.objects.create(plan=ctx["empresa"].plan, funcionalidad_id=f)


def crear_token(ctx, nombre, tecnico="n8n"):
    almacen = rol_id(ctx["empresa"], "Almacén")
    token = caso_de_tokens(CrearTokenApi).ejecutar(
        actor("lucia@andina.pe"), nombre, tecnico, [almacen], hoy()
    )
    ctx.setdefault("tokens", {})[nombre] = token
    ctx["token"] = token
    return token


def llamar(client, token):
    client.logout()
    return client.get("/api/prueba/", HTTP_AUTHORIZATION=f"Token {token}")


@when(
    re_(
        "{} crea el token {} para el usuario técnico {} con el rol {}",
        "email",
        "nombre",
        "tecnico",
        "rol",
    )
)
def crea_token(client, ctx, email, nombre, tecnico, rol):
    datos = {
        "accion": "crear",
        "nombre": nombre,
        "tecnico": tecnico,
        "roles": [rol_id(ctx["empresa"], rol)],
    }
    ctx["respuesta"] = como(client, email).post("/integracion/tokens/", datos)
    ctx["token"] = re.search(r'<code id="token-nuevo">([^<]+)</code>', contenido(ctx["respuesta"]))[
        1
    ]


@then('ve el token completo una sola vez con el botón "Copiar"')
def ve_token_una_vez(ctx):
    assert "Copiar" in contenido(ctx["respuesta"])
    assert ApiToken.all_tenants.filter(token_hash=hash_token(ctx["token"])).exists()


@then("al recargar la página solo ve su prefijo, la fecha de creación y el último uso")
def al_recargar(client, ctx):
    pagina = contenido(client.get("/integracion/tokens/"))
    assert ctx["token"] not in pagina and f"<code>{ctx['token'][:8]}…</code>" in pagina
    assert "Creado" in pagina and "Último uso" in pagina


@then(re_("la auditoría registra la creación del token {}", "nombre"))
def auditoria_creacion(nombre):
    fila = AuditoriaAcceso.all_tenants.get(entidad="TOKEN_API", accion="CREAR")
    assert fila.despues["nombre"] == nombre and fila.actor.email == "lucia@andina.pe"


@given(re_("el token {} de {}", "nombre", "empresa"))
def token_de(ctx, nombre, empresa):
    crear_token(ctx, nombre)


@when("una integración consulta el stock con ese token")
def consulta_con_token(client, ctx):
    brew = empresa_por_nombre("Brew Lima")
    if not Rol.all_tenants.filter(empresa=brew).exists():
        asignar_rol(Usuario.objects.create_user("x@brew.pe", "x", empresa=brew))
    ctx["respuesta"] = llamar(client, ctx["token"])


@then(re_("recibe solo productos de {}, paginados", "nombre"))
def recibe_solo_de(ctx, nombre):
    datos = ctx["respuesta"].json()
    assert ctx["respuesta"].status_code == 200 and "count" in datos and "next" in datos
    assert {r["empresa_id"] for r in datos["results"]} == {empresa_por_nombre(nombre).id}
    ctx["pendientes"].append("la consulta de stock llega con 0003c; se usó una consulta de prueba")


@then(re_("no recibe datos de {}", "nombre"))
def no_recibe_de(ctx, nombre):
    ids = {r["empresa_id"] for r in ctx["respuesta"].json()["results"]}
    assert empresa_por_nombre(nombre).id not in ids


@when(re_("{} revoca {}", "email", "nombre"))
def revoca(client, ctx, email, nombre):
    token = ApiToken.all_tenants.get(token_hash=hash_token(ctx["tokens"][nombre]))
    como(client, email).post("/integracion/tokens/", {"accion": "revocar", "token": token.id})


@then("la siguiente llamada con ese token es rechazada como no autenticada")
def siguiente_rechazada(client, ctx):
    assert llamar(client, ctx["token"]).status_code == 401


@then("la auditoría registra la revocación")
def auditoria_revocacion():
    fila = AuditoriaAcceso.all_tenants.get(entidad="TOKEN_API", accion="REVOCAR")
    assert fila.despues["revocado"] is True


@given(re_("que el usuario técnico {} tiene los tokens {} y {}", "tecnico", "t1", "t2"))
def tecnico_con_tokens(ctx, tecnico, t1, t2):
    crear_token(ctx, t1, tecnico)
    crear_token(ctx, t2, tecnico)


@when(re_("{} desactiva el usuario técnico {}", "email", "tecnico"))
def desactiva_tecnico(client, ctx, email, tecnico):
    usuario = Usuario.objects.get(es_tecnico=True, nombre=tecnico)
    como(client, email).post(
        "/integracion/tokens/", {"accion": "desactivar_tecnico", "usuario": usuario.id}
    )


@then(re_("las llamadas con {} y con {} son rechazadas como no autenticadas", "t1", "t2"))
def ambas_rechazadas(client, ctx, t1, t2):
    for nombre in (t1, t2):
        assert llamar(client, ctx["tokens"][nombre]).status_code == 401


@given(re_("que {} está suspendida", "nombre"))
def suspendida(nombre):
    Empresa.objects.filter(razon_social=nombre).update(estado="SUSPENDIDA")


@given(re_("que la suscripción de {} venció ayer", "nombre"))
def vencio_ayer(nombre):
    Empresa.objects.filter(razon_social=nombre).update(fecha_termino=hoy() - timedelta(days=1))


@given('que la funcionalidad "API de integración" fue quitada a la empresa')
def api_quitada(ctx):
    plataforma().quitar(ctx["empresa"].id, [API], "Baja", None, None, hoy(), True)


@then("la llamada es rechazada")
def llamada_rechazada(ctx):
    assert ctx["respuesta"].status_code in (401, 403)


@given(re_('que la funcionalidad "API de integración" no está habilitada para {}', "nombre"))
def api_no_habilitada(ctx, nombre):
    plataforma().quitar(ctx["empresa"].id, [API], "Baja", None, None, hoy(), True)


@when(re_("{} intenta crear un token", "email"))
def intenta_crear_token(client, ctx, email):
    datos = {"accion": "crear", "nombre": "x", "tecnico": "n8n"}
    ctx["respuesta"] = como(client, email).post("/integracion/tokens/", datos)
