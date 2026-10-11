"""Acceso en cada request (spec 0001c; RF-TEN-40 a 42, 49, 52).

`AccesoMiddleware` arma el `Actor` del usuario en cada request, así un cambio de roles o
de habilitaciones aplica desde su siguiente acción sin cerrar su sesión.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone

from shared.domain.errores import AccesoDenegado, NoEncontrado
from tenancy.infrastructure.contenedor import actor_de

SIN_MODULOS = "No tienes módulos asignados. Contacta al administrador de tu empresa"
RUTAS_SIN_PERMISO = ("/logout/", "/static/", "/media/")


class AccesoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.actor = None
        usuario = request.user
        if usuario.is_authenticated and usuario.empresa_id:
            request.actor = actor_de(usuario, timezone.localdate())
            if not request.actor.permisos and not request.path.startswith(RUTAS_SIN_PERMISO):
                return render(request, "tenancy/sin_modulos.html", {"mensaje": SIN_MODULOS})
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Los casos de uso lanzan errores de dominio; aquí se vuelven 403 o 404."""
        if isinstance(exception, AccesoDenegado):
            return render(request, "403.html", {"mensaje": exception.mensaje}, status=403)
        if isinstance(exception, NoEncontrado):
            return render(request, "404.html", status=404)
        return None


def requiere(permiso: str):
    """Verifica el permiso de la vista en el servidor (RF-TEN-49)."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envuelta(request, *args, **kwargs):
            if request.actor is None:
                raise PermissionDenied
            request.actor.exige(permiso)
            return vista(request, *args, **kwargs)

        return envuelta

    return decorador


def permisos(request):
    """Context processor: `{% if "ventas.venta.anular" in permisos %}` (RF-TEN-50)."""
    actor = getattr(request, "actor", None)
    return {"permisos": actor.permisos if actor else frozenset()}
