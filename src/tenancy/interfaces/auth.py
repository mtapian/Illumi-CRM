"""Inicio de sesión con control de intentos (UC-TEN-02; RF-TEN-06 a 08)."""

from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from tenancy.domain.sesion import bloqueo_por_intentos, esta_bloqueado
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import Usuario
from tenancy.interfaces.forms import LoginForm

BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"
CREDENCIALES_INCORRECTAS = "Email o contraseña incorrectos"
BLOQUEADO = (
    "Tu usuario está bloqueado temporalmente por intentos fallidos. Intenta de nuevo en 15 minutos."
)
INACTIVO = "Tu usuario está desactivado. Contacta al administrador."
SUSPENDIDA = "Tu empresa está suspendida. Contacta a soporte de Illumi."


def _validar(email: str, password: str) -> tuple[Usuario | None, str | None]:
    usuario = Usuario.objects.filter(email__iexact=email.strip()).first()
    if usuario is None or usuario.es_tecnico:
        return None, CREDENCIALES_INCORRECTAS
    ahora = timezone.now()
    if esta_bloqueado(usuario.bloqueado_hasta, ahora):
        return None, BLOQUEADO
    if not usuario.check_password(password):
        usuario.intentos_fallidos += 1
        usuario.bloqueado_hasta = bloqueo_por_intentos(usuario.intentos_fallidos, ahora)
        if usuario.bloqueado_hasta:
            usuario.intentos_fallidos = 0
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return None, BLOQUEADO if usuario.bloqueado_hasta else CREDENCIALES_INCORRECTAS
    if not usuario.is_active:
        return None, INACTIVO
    if usuario.empresa and usuario.empresa.estado == Estado.SUSPENDIDA:
        return None, SUSPENDIDA
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
    return usuario, None


def iniciar_sesion(request):
    form = LoginForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        usuario, error = _validar(form.cleaned_data["email"], form.cleaned_data["password"])
        if usuario:
            login(request, usuario, backend=BACKEND)
            return redirect("plataforma" if usuario.is_super else "dashboard")
    return render(request, "tenancy/login.html", {"form": form, "error": error})


@require_POST
def cerrar_sesion(request):
    logout(request)
    return redirect("login")
