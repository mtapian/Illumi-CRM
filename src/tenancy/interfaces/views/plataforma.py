"""Pantallas del super admin (spec 0001b, plan §5). Solo `is_super`; el resto recibe 403."""

from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from shared.domain.accesos import CATALOGO, MODULOS
from shared.domain.documentos import (
    ALFANUMERICO,
    DIGITOS,
    NINGUNA,
    VALIDACION_RUC,
    ReglasDocumento,
)
from shared.domain.errores import DomainError
from tenancy.domain.habilitaciones import estado_funcionalidad, funcionalidades_de_modulo
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.contenedor import guardar_tipo_documento, plataforma
from tenancy.infrastructure.models import Actividad, AuditoriaAcceso, Empresa, Plan, TipoDocumento
from tenancy.infrastructure.repositorios import HabilitacionesOrm, funcionalidades_de_plan
from tenancy.interfaces.views.auditoria_tokens import filas_auditoria


def solo_super(vista):
    @login_required
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not request.user.is_super:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envuelta


def _fecha(texto: str) -> date | None:
    return date.fromisoformat(texto) if texto else None


def _modulos_con_funcionalidades(incluir_core=False):
    return [
        {
            "codigo": m,
            "nombre": nombre,
            "funcionalidades": funcionalidades_de_modulo(m),
            "opciones": [
                {"codigo": f, "nombre": CATALOGO[f].nombre} for f in funcionalidades_de_modulo(m)
            ],
        }
        for m, nombre in MODULOS.items()
        if incluir_core or m != "CORE"
    ]


# --- UC-TEN-06: empresas (RF-TEN-22 a 24) ---


@solo_super
def empresas(request):
    filas = Empresa.objects.select_related("plan").order_by("razon_social")
    estado, plan = request.GET.get("estado", ""), request.GET.get("plan", "")
    if estado:
        filas = filas.filter(estado=estado)
    if plan:
        filas = filas.filter(plan_id=plan)
    contexto = {
        "empresas": filas,
        "estados": list(Estado),
        "planes": Plan.objects.order_by("nombre"),
        "filtro": {"estado": estado, "plan": plan},
    }
    return render(request, "tenancy/plataforma/empresas.html", contexto)


@solo_super
def empresa(request, empresa_id):
    empresa = get_object_or_404(Empresa.objects.select_related("plan"), pk=empresa_id)
    if request.method == "POST":
        p, datos, actor = plataforma(), request.POST, request.user.id
        accion, motivo = datos.get("accion"), datos.get("motivo", "")
        try:
            if accion == "activar":
                p.activar_plan(
                    empresa.id, int(datos["plan"]), _fecha(datos.get("hasta")), motivo, actor
                )
            elif accion == "cambiar_plan":
                p.cambiar_plan(empresa.id, int(datos["plan"]), motivo, actor)
            elif accion == "suspender":
                p.suspender(empresa.id, motivo, actor)
            elif accion == "reactivar":
                p.reactivar(empresa.id, motivo, actor)
            messages.success(request, "Cambio guardado.")
            return redirect("plataforma_empresa", empresa_id=empresa.id)
        except DomainError as e:
            messages.error(request, e.mensaje)
    contexto = {
        "empresa": empresa,
        "planes": Plan.objects.filter(activo=True).order_by("nombre"),
        "actividad": Actividad.objects.filter(empresa=empresa)
        .select_related("actor")
        .order_by("-created_at")[:20],
        "filas": filas_auditoria(AuditoriaAcceso.all_tenants.filter(empresa=empresa)),
    }
    return render(request, "tenancy/plataforma/empresa.html", contexto)


# --- UC-TEN-07: planes (RF-TEN-25 a 27) ---


@solo_super
def planes(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            nuevo = Plan.objects.create(
                nombre=nombre, slug=request.POST.get("slug") or nombre.lower()
            )
            return redirect("plataforma_plan", plan_id=nuevo.id)
    filas = Plan.objects.annotate(n_empresas=Count("empresas_plan")).order_by("nombre")
    return render(request, "tenancy/plataforma/planes.html", {"planes": filas})


def _limite(texto: str) -> int | None:
    return int(texto) if texto.strip() else None


@solo_super
def plan(request, plan_id):
    plan = get_object_or_404(Plan, pk=plan_id)
    elegidas = funcionalidades_de_plan(plan.id)
    contexto = {"plan": plan, "modulos": _modulos_con_funcionalidades()}
    if request.method == "POST":
        elegidas = set(request.POST.getlist("funcionalidades"))
        limites = {
            "limite_usuarios": _limite(request.POST.get("limite_usuarios", "")),
            "limite_productos": _limite(request.POST.get("limite_productos", "")),
        }
        confirmado = request.POST.get("confirmado") == "1"
        try:
            afectadas = plataforma().configurar_plan(plan.id, elegidas, limites, confirmado)
            if confirmado:
                messages.success(request, f"Plan actualizado para {afectadas} empresas.")
                return redirect("plataforma_plan", plan_id=plan.id)
            contexto |= {"confirmar": afectadas, "limites": limites}
        except DomainError as e:
            messages.error(request, e.mensaje)
    contexto["elegidas"] = elegidas
    return render(request, "tenancy/plataforma/plan.html", contexto)


# --- UC-TEN-08: módulos y funcionalidades de una empresa (RF-TEN-28 a 34) ---


@solo_super
def modulos(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    hoy = timezone.localdate()
    contexto = {"empresa": empresa}
    if request.method == "POST":
        datos = request.POST
        objetivo = datos.get("objetivo", "")  # "M:<MODULO>" o código de funcionalidad (RF-TEN-34)
        funcs = funcionalidades_de_modulo(objetivo[2:]) if objetivo.startswith("M:") else [objetivo]
        args = (empresa.id, funcs, datos.get("motivo", ""), _fecha(datos.get("hasta")))
        try:
            if datos.get("accion") == "agregar":
                plataforma().agregar(*args, request.user.id, hoy)
                advertencias = []
            else:
                confirmado = datos.get("confirmado") == "1"
                advertencias = plataforma().quitar(*args, request.user.id, hoy, confirmado)
            if not advertencias:
                messages.success(request, "Cambio guardado.")
                return redirect("plataforma_modulos", empresa_id=empresa.id)
            contexto["confirmar"] = {"advertencias": advertencias, "datos": datos}
        except DomainError as e:
            messages.error(request, e.mensaje)
    repo = HabilitacionesOrm()
    funcs_plan, ajustes = repo.funcionalidades_plan(empresa.id), repo.ajustes(empresa.id)
    hasta = {a.funcionalidad: a.vigente_hasta for a in ajustes}
    contexto["modulos"] = [
        m
        | {
            "filas": [
                {
                    "codigo": f,
                    "nombre": CATALOGO[f].nombre,
                    "estado": estado_funcionalidad(f, funcs_plan, ajustes, hoy),
                    "hasta": hasta.get(f),
                }
                for f in m["funcionalidades"]
            ]
        }
        for m in _modulos_con_funcionalidades(incluir_core=True)
    ]
    return render(request, "tenancy/plataforma/modulos.html", contexto)


# --- 0006a: tipos de documento (RF-VEN-49) ---

CAMPOS_TIPO = ("abreviatura", "codigo_sunat", "nombre", "longitud_min", "longitud_max")
CAMPOS_TIPO += ("caracteres", "validacion")


def _entero(texto) -> int:
    return int(texto) if str(texto).strip().isdigit() else 0


@solo_super
def tipos_documento(request):
    """Listado de maestro (ADR-12) y formulario; sin eliminar: un tipo se desactiva."""
    editar = request.GET.get("editar", "")
    if request.method == "POST":
        p = request.POST
        id_ = int(p["id"]) if p.get("id", "").isdigit() else None
        reglas = ReglasDocumento(
            p.get("abreviatura", ""),
            p.get("codigo_sunat", ""),
            p.get("nombre", ""),
            p.get("exige_numero") == "on",
            _entero(p.get("longitud_min")),
            _entero(p.get("longitud_max")),
            p.get("caracteres", ""),
            p.get("validacion", ""),
            p.get("activo") == "on",
        )
        try:
            guardar_tipo_documento().ejecutar(id_, reglas)
            messages.success(request, "Tipo de documento guardado.")
            return redirect("plataforma_tipos_documento")
        except DomainError as e:
            messages.error(request, e.mensaje)
            editar = str(id_ or "")
    filas = TipoDocumento.objects.order_by("codigo_sunat")
    editando = get_object_or_404(TipoDocumento, pk=editar) if editar.isdigit() else None
    valores = request.POST if request.method == "POST" else editando
    contexto = {
        "filas": filas,
        "editando": editando,
        "nuevo": "nuevo" in request.GET or (request.method == "POST" and not editando),
        "valores": valores,
        "caracteres": [(DIGITOS, "Solo dígitos"), (ALFANUMERICO, "Letras y números")],
        "validaciones": [(NINGUNA, "Ninguna"), (VALIDACION_RUC, "Dígito verificador del RUC")],
    }
    return render(request, "tenancy/plataforma/tipos_documento.html", contexto)
