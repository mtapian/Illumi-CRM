"""Empresa de cada request y control de suscripción (plan 0000 §4; RF-TEN-18 y 21)."""

from django.shortcuts import redirect
from django.utils import timezone

from shared.domain.tenant import tenant_context
from tenancy.domain.suscripcion import puede_operar

RUTAS_SIEMPRE_DISPONIBLES = ("/suscripcion/", "/logout/", "/login/", "/password-reset/", "/static/")


class TenantMiddleware:
    """Fija la empresa del usuario durante el request. El super admin no tiene empresa."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa_id = getattr(request.user, "empresa_id", None)
        if empresa_id is None:
            return self.get_response(request)
        with tenant_context(empresa_id):
            return self.get_response(request)


class SuscripcionMiddleware:
    """Con la prueba o la suscripción vencida, o la empresa suspendida, solo se puede ver la
    suscripción y cerrar sesión. Se evalúa en cada request, así que una suspensión bloquea
    la siguiente acción de una sesión abierta."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa = getattr(request.user, "empresa", None)
        if (
            empresa is not None
            and not request.path.startswith(RUTAS_SIEMPRE_DISPONIBLES)
            and not puede_operar(empresa.estado, empresa.fecha_termino, timezone.localdate())
        ):
            return redirect("/suscripcion/")
        return self.get_response(request)
