"""Pantallas de auditoría de accesos y de tokens de API (spec 0001d, plan §5)."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from shared.domain.auditoria import diferencias
from shared.domain.errores import AccesoDenegado
from shared.interfaces import listados
from tenancy.application import tokens as uc_tokens
from tenancy.domain.tokens import API
from tenancy.infrastructure.contenedor import caso_de_tokens, tenancy_service
from tenancy.infrastructure.models import ApiToken, AuditoriaAcceso, Rol, Usuario
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _ids, _intentar


def filas_auditoria(consulta):
    """Filas para mostrar: quién, cuándo, qué y el valor anterior → nuevo (RF-TEN-44)."""
    return [
        {
            "fecha": a.created_at,
            "autor": a.actor.email if a.actor else "Sistema",
            "entidad": a.entidad,
            "nombre": (a.despues or a.antes or {}).get("nombre", f"#{a.entidad_id}"),
            "accion": a.accion,
            "cambios": diferencias(a.antes, a.despues),
        }
        for a in consulta.select_related("actor").order_by("-created_at", "-id")[:200]
    ]


@requiere("core.auditoria.ver")
def auditoria(request):
    filtro = {k: request.GET.get(k, "") for k in ("desde", "hasta", "entidad", "autor")}
    consulta = AuditoriaAcceso.objects.all()
    if filtro["desde"]:
        consulta = consulta.filter(created_at__date__gte=date.fromisoformat(filtro["desde"]))
    if filtro["hasta"]:
        consulta = consulta.filter(created_at__date__lte=date.fromisoformat(filtro["hasta"]))
    if filtro["entidad"]:
        consulta = consulta.filter(entidad=filtro["entidad"])
    if filtro["autor"]:
        consulta = consulta.filter(actor__email__icontains=filtro["autor"])
    contexto = {
        "filas": filas_auditoria(consulta),
        "filtro": filtro,
        "entidades": [e for e, _ in AuditoriaAcceso.ENTIDADES],
        "aplicados": listados.aplicados(
            request,
            {k: (k.capitalize(), None) for k in ("autor", "entidad", "desde", "hasta")},
        ),
    }
    return render(request, "tenancy/auditoria.html", contexto)


@login_required
def tokens(request):
    """Tokens de API (RF-TEN-45 a 47, 54). Sin la API habilitada se explica por qué no."""
    actor, hoy = request.actor, timezone.localdate()
    if actor is None or "api.token.gestionar" not in actor.permisos_rol:
        raise AccesoDenegado("Acceso denegado")
    if API not in tenancy_service().habilitaciones_de(actor.empresa_id, hoy):
        if request.method == "POST":
            messages.error(request, uc_tokens.SIN_API)
        return render(request, "tenancy/tokens.html", {"sin_api": uc_tokens.SIN_API}, status=403)
    actor.exige("api.token.gestionar")
    nuevo = None
    if request.method == "POST":
        p, accion = request.POST, request.POST.get("accion")
        if accion == "crear":
            caso, resultado = caso_de_tokens(uc_tokens.CrearTokenApi), {}
            if _intentar(
                request,
                lambda: resultado.update(
                    token=caso.ejecutar(actor, p["nombre"], p["tecnico"], _ids(request), hoy)
                ),
            ):
                nuevo = resultado["token"]  # se muestra esta única vez, sin redirigir
        else:
            if accion == "revocar":
                caso = caso_de_tokens(uc_tokens.RevocarTokenApi)
                hecho = _intentar(request, lambda: caso.ejecutar(actor, int(p["token"])))
            else:
                caso = caso_de_tokens(uc_tokens.DesactivarUsuarioTecnico)
                hecho = _intentar(request, lambda: caso.ejecutar(actor, int(p["usuario"])))
            if hecho:
                messages.success(request, "Cambio guardado.")
            return redirect("tokens")
    contexto = {
        "nuevo": nuevo,
        "tokens": ApiToken.objects.select_related("usuario").order_by("-creado_en"),
        "tecnicos": Usuario.objects.filter(empresa_id=actor.empresa_id, es_tecnico=True),
        "roles": Rol.objects.filter(activo=True).order_by("-es_sistema", "nombre"),
    }
    return render(request, "tenancy/tokens.html", contexto)
