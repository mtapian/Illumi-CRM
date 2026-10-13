"""Pasos de modulos_funcionalidades.feature y suscripcion_plataforma.feature (0001b)."""

import re
from datetime import date, timedelta

import pytest
from django.test import Client
from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from shared.domain.accesos import CATALOGO, CORE
from tenancy.application.operaciones_en_curso import ContadorOperacionesEnCurso, contadores
from tenancy.domain.habilitaciones import funcionalidades_de_modulo
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.contenedor import plataforma, tenancy_service
from tenancy.infrastructure.models import (
    Actividad,
    Empresa,
    EmpresaAjuste,
    Plan,
    PlanFuncionalidad,
    Usuario,
)
from tenancy.infrastructure.repositorios import funcionalidades_de_plan
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_sesion import crear_usuario, iniciar_sesion, ruc_valido

Q = r'"(?P<{}>[^"]+)"'


def re_(texto: str, *nombres: str):
    """Paso con valores entre comillas: `{}` se reemplaza por un grupo que no cruza comillas."""
    return parsers.re(texto.format(*(Q.format(n) for n in nombres)))


def por_nombre(nombre: str) -> str:
    return next(c for c, f in CATALOGO.items() if f.nombre == nombre)


def hoy() -> date:
    return timezone.localdate()


def plan(nombre: str) -> Plan:
    return Plan.objects.get_or_create(nombre=nombre, defaults={"slug": nombre.lower()})[0]


def empresa(nombre: str) -> Empresa:
    existente = Empresa.objects.filter(razon_social=nombre).first()
    return existente or Empresa.objects.create(
        ruc=ruc_valido(),
        razon_social=nombre,
        plan=plan("Emprendedor"),
        estado=Estado.ACTIVA,
        fecha_termino=hoy() + timedelta(days=30),
    )


@pytest.fixture
def super_admin(client):
    usuario, _ = Usuario.objects.get_or_create(
        email="super@illumi.pe", defaults={"nombre": "Super", "is_super": True}
    )
    client.force_login(usuario, backend="tenancy.infrastructure.auth_backend.EmailBackend")
    return usuario


def url_modulos(nombre: str) -> str:
    return f"/plataforma/empresas/{empresa(nombre).id}/modulos/"


def post_modulos(client, ctx, nombre, accion, objetivo, motivo="", hasta="", confirmado=False):
    datos = {"accion": accion, "objetivo": objetivo, "motivo": motivo, "hasta": hasta}
    if confirmado:
        datos["confirmado"] = "1"
    ctx["respuesta"] = client.post(url_modulos(nombre), datos, follow=True)


def fila_con_estado(pagina: str, funcionalidad: str, estado: str) -> bool:
    patron = rf'<td>{funcionalidad}</td>\s*<td><span class="estado-func[^"]*">{estado}</span>'
    return re.search(patron, pagina) is not None


# --- Antecedentes ---


@given("que soy super admin de la plataforma")
def soy_super_admin(super_admin, ctx):
    ctx["super"] = super_admin


@given(re_("el plan {} incluye las funcionalidades:", "nombre"))
def plan_incluye(ctx, nombre, datatable):
    p = plan(nombre)
    for fila in datatable[1:]:
        PlanFuncionalidad.objects.create(plan=p, funcionalidad_id=por_nombre(fila[1]))
    ctx["plan_inicial"] = funcionalidades_de_plan(p.id)


@given(re_("la empresa {} tiene el plan {}", "nombre", "plan_nombre"))
def empresa_con_plan(nombre, plan_nombre):
    Empresa.objects.filter(pk=empresa(nombre).pk).update(plan=plan(plan_nombre))


# --- Planes (UC-TEN-07) ---


@given(re_(r"que (?P<n>\d+) empresas tienen el plan {}", "nombre"))
def n_empresas(n, nombre):
    for i in range(int(n) - Empresa.objects.filter(plan=plan(nombre)).count()):
        Empresa.objects.create(ruc=ruc_valido(), razon_social=f"Empresa {i}", plan=plan(nombre))


@when(re_("agrego al plan {} la funcionalidad {}", "nombre", "funcionalidad"))
def agrego_al_plan(client, ctx, nombre, funcionalidad):
    p = plan(nombre)
    ctx["plan_post"] = {
        "funcionalidades": [*funcionalidades_de_plan(p.id), por_nombre(funcionalidad)],
        "limite_usuarios": "",
        "limite_productos": "",
    }
    ctx["plan"] = p
    ctx["respuesta"] = client.post(f"/plataforma/planes/{p.id}/", ctx["plan_post"], follow=True)


@then(re_("veo el aviso {} antes de confirmar", "texto"))
def veo_aviso(ctx, texto):
    assert texto in contenido(ctx["respuesta"])


@then(re_(r"al confirmar, {} queda habilitada para las (?P<n>\d+) empresas", "funcionalidad"))
def al_confirmar(client, ctx, funcionalidad, n):
    client.post(f"/plataforma/planes/{ctx['plan'].id}/", ctx["plan_post"] | {"confirmado": "1"})
    empresas = Empresa.objects.filter(plan=ctx["plan"])
    assert empresas.count() == int(n)
    for e in empresas:
        assert por_nombre(funcionalidad) in tenancy_service().habilitaciones_de(e.id, hoy())


# --- Ajustes por empresa (UC-TEN-08) ---


@when(
    re_("agrego a {} el módulo {} hasta el {} con motivo {}", "nombre", "modulo", "fecha", "motivo")
)
def agrego_modulo(client, ctx, nombre, modulo, fecha, motivo):
    ctx["motivo"] = motivo
    post_modulos(client, ctx, nombre, "agregar", f"M:{modulo}", motivo, fecha)


@then(re_(r"{} tiene habilitadas? (?P<lista>.+) con estado {}", "nombre", "estado"))
def tiene_habilitadas(client, nombre, lista, estado):
    pagina = contenido(client.get(url_modulos(nombre)))
    for funcionalidad in re.findall(r'"([^"]+)"', lista):
        assert fila_con_estado(pagina, funcionalidad, estado), funcionalidad


@then(re_("el plan {} no cambia", "nombre"))
def plan_no_cambia(ctx, nombre):
    assert funcionalidades_de_plan(plan(nombre).id) == ctx["plan_inicial"]


@then(parsers.parse("el registro de actividad guarda la acción, el super admin, {campos}"))
def registro_actividad(ctx, campos):
    actividad = Actividad.objects.latest("id")
    assert actividad.accion and actividad.actor == ctx["super"] and actividad.created_at
    assert actividad.motivo == ctx["motivo"]
    if "vigencia" in campos:
        assert actividad.detalle["hasta"]


@given(re_("que {} tiene agregado el módulo {} hasta el {}", "nombre", "modulo", "fecha"))
def tiene_modulo_hasta(ctx, nombre, modulo, fecha):
    hasta = date.fromisoformat(fecha)
    funcs = funcionalidades_de_modulo(modulo)
    plataforma().agregar(empresa(nombre).id, funcs, "Piloto", hasta, None, hasta)


@when(re_("llega el {}", "fecha"))
def llega_el(ctx, fecha):
    ctx["hoy"] = date.fromisoformat(fecha)


@then(re_("{} deja de tener habilitado el módulo {}", "nombre", "modulo"))
def deja_de_tener(ctx, nombre, modulo):
    hab = tenancy_service().habilitaciones_de(empresa(nombre).id, ctx["hoy"])
    assert not hab & set(funcionalidades_de_modulo(modulo))


@then("sus datos de producción se conservan")
def datos_produccion_se_conservan():
    # El ajuste vencido no se borró ni se revocó: solo dejó de aplicarse (RN-GEN-11). Las OP
    # (0005a) son datos de la empresa: un módulo deshabilitado no las borra (art. 3.3).
    assert EmpresaAjuste.objects.filter(revocado_en__isnull=True).count() == 1


@when(re_("quito a {} la funcionalidad {} con motivo {}", "nombre", "funcionalidad", "motivo"))
def quito_con_motivo(client, ctx, nombre, funcionalidad, motivo):
    post_modulos(client, ctx, nombre, "quitar", por_nombre(funcionalidad), motivo)


@then(re_("{} aparece como {} para {}", "funcionalidad", "estado", "nombre"))
def aparece_como(client, funcionalidad, estado, nombre):
    assert fila_con_estado(contenido(client.get(url_modulos(nombre))), funcionalidad, estado)


@then(re_("las demás empresas del plan {} la conservan", "nombre"))
def demas_la_conservan(nombre):
    otra = empresa("Brew Lima")
    Empresa.objects.filter(pk=otra.pk).update(plan=plan(nombre))
    assert "inventario.ajustes" in tenancy_service().habilitaciones_de(otra.id, hoy())


@when(re_("quito a {} la funcionalidad {}$", "nombre", "funcionalidad"))
def quito(client, ctx, nombre, funcionalidad):
    post_modulos(client, ctx, nombre, "quitar", por_nombre(funcionalidad), "Prueba")


@when(re_("agrego a {} la funcionalidad {} sin motivo", "nombre", "funcionalidad"))
def agrego_sin_motivo(client, ctx, nombre, funcionalidad):
    post_modulos(client, ctx, nombre, "agregar", por_nombre(funcionalidad))


@then(re_("la operación es rechazada con el mensaje {}", "mensaje"))
def rechazada(ctx, mensaje):
    assert mensaje in contenido(ctx["respuesta"])


@when(re_("intento quitar a {} el módulo {}", "nombre", "modulo"))
def intento_quitar_modulo(client, ctx, nombre, modulo):
    ctx["pagina"] = contenido(client.get(url_modulos(nombre)))
    ctx["modulo"] = modulo
    post_modulos(client, ctx, nombre, "quitar", f"M:{modulo}", "Prueba", confirmado=True)


@then("la operación no está disponible")
def no_disponible(ctx, client):
    assert f'value="M:{ctx["modulo"]}"' not in ctx["pagina"]
    assert "CORE no se puede deshabilitar" in contenido(ctx["respuesta"])
    assert CORE <= tenancy_service().habilitaciones_de(empresa("Cervecería Andina").id, hoy())


@given(re_("que {} tiene agregado el módulo {}$", "nombre", "modulo"))
def tiene_modulo(nombre, modulo):
    funcs = funcionalidades_de_modulo(modulo)
    plataforma().agregar(empresa(nombre).id, funcs, "Piloto", None, None, hoy())


@given(re_(r"tiene (?P<n>\d+) OP en estado {}", "estado"))
def tiene_op(monkeypatch, n, estado):
    # Contador falso: el real lo registra la épica 0005 (plan 0001b §9).
    contador = ContadorOperacionesEnCurso(
        "produccion.op",
        lambda _: int(n),
        "La empresa tiene {n} OP en proceso; quedarán sin poder operarse",
    )
    monkeypatch.setattr(contadores, "_contadores", [contador])


@when(re_("quito a {} el módulo {}", "nombre", "modulo"))
def quito_modulo(client, ctx, nombre, modulo):
    post_modulos(client, ctx, nombre, "quitar", f"M:{modulo}", "Fin del piloto")


@then(re_("veo la advertencia {} antes de confirmar", "texto"))
def veo_advertencia(ctx, texto):
    assert texto in contenido(ctx["respuesta"])
    hab = tenancy_service().habilitaciones_de(empresa("Cervecería Andina").id, hoy())
    assert "produccion.op" in hab  # todavía no se quitó


@given(re_("que {} tiene agregado el módulo {} sin vigencia", "nombre", "modulo"))
def tiene_modulo_sin_vigencia(nombre, modulo):
    tiene_modulo(nombre, modulo)


@when(re_("cambio a {} al plan {}", "nombre", "plan_nombre"))
def cambio_plan(client, ctx, nombre, plan_nombre):
    negocio = plan(plan_nombre)
    for f in ctx["plan_inicial"] | {"inventario.multialmacen", "inventario.lotes"}:
        PlanFuncionalidad.objects.get_or_create(plan=negocio, funcionalidad_id=f)
    client.post(
        f"/plataforma/empresas/{empresa(nombre).id}/",
        {"accion": "cambiar_plan", "plan": negocio.id, "motivo": "Upgrade"},
    )


@then(re_("sus habilitaciones son las del plan {} más el módulo {}", "plan_nombre", "modulo"))
def habilitaciones_plan_mas_modulo(plan_nombre, modulo):
    esperado = (
        funcionalidades_de_plan(plan(plan_nombre).id)
        | set(funcionalidades_de_modulo(modulo))
        | CORE
    )
    hab = tenancy_service().habilitaciones_de(empresa("Cervecería Andina").id, hoy())
    assert hab == esperado


@given(re_("que {} tiene agregado {} y quitado {}", "nombre", "agregada", "quitada"))
def agregado_y_quitado(nombre, agregada, quitada):
    e = empresa(nombre).id
    plataforma().agregar(e, [por_nombre(agregada)], "Piloto", None, None, hoy())
    plataforma().quitar(e, [por_nombre(quitada)], "Pedido", None, None, hoy(), True)


@when(re_('abro "Módulos y funcionalidades" de {}', "nombre"))
def abro_modulos(client, ctx, nombre):
    ctx["pagina"] = contenido(client.get(url_modulos(nombre)))


@then("veo:")
def veo_tabla(ctx, datatable):
    for funcionalidad, estado in datatable[1:]:
        assert fila_con_estado(ctx["pagina"], funcionalidad, estado), funcionalidad


# --- suscripcion_plataforma.feature (UC-TEN-06) ---


@given(re_("que {} tiene la prueba vencida", "nombre"))
def prueba_vencida(ctx, nombre):
    e = empresa(nombre)
    Empresa.objects.filter(pk=e.pk).update(
        estado=Estado.TRIAL, fecha_termino=hoy() - timedelta(days=1)
    )
    crear_usuario("ana@andina.pe", e)


@when(
    re_(
        "el super admin activa el plan {} hasta el {} con el motivo {}",
        "plan_nombre",
        "fecha",
        "motivo",
    )
)
def activa_plan(client, super_admin, ctx, plan_nombre, fecha, motivo):
    ctx["super"], ctx["motivo"] = super_admin, motivo
    e = empresa("Cervecería Andina")
    client.post(
        f"/plataforma/empresas/{e.id}/",
        {"accion": "activar", "plan": plan(plan_nombre).id, "hasta": fecha, "motivo": motivo},
    )


@then(re_("la empresa queda en estado {} hasta el {}", "estado", "fecha"))
def queda_en_estado_hasta(estado, fecha):
    e = empresa("Cervecería Andina")
    assert (e.estado, e.fecha_termino) == (estado.upper(), date.fromisoformat(fecha))


@then("sus usuarios pueden operar normalmente")
def usuarios_operan():
    usuario = Client()
    respuesta = iniciar_sesion(usuario, "ana@andina.pe")
    assert respuesta.redirect_chain[-1][0] == "/dashboard/"
    assert usuario.get("/dashboard/").status_code == 200


@when(re_("el super admin suspende {} con el motivo {}", "nombre", "motivo"))
def suspende(client, super_admin, ctx, nombre, motivo):
    e = empresa(nombre)
    ctx["estado_antes"] = e.estado
    client.post(f"/plataforma/empresas/{e.id}/", {"accion": "suspender", "motivo": motivo})


@then(re_("la empresa queda en estado {}$", "estado"))
def queda_en_estado(estado):
    assert empresa("Cervecería Andina").estado == estado.upper()


@when("el super admin la reactiva")
def reactiva(client):
    e = empresa("Cervecería Andina")
    client.post(f"/plataforma/empresas/{e.id}/", {"accion": "reactivar", "motivo": "Pagó"})


@then("la empresa vuelve al estado anterior a la suspensión")
def vuelve_al_estado_anterior(ctx):
    assert empresa("Cervecería Andina").estado == ctx["estado_antes"]
