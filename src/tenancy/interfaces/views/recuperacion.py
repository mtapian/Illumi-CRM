"""Recuperar contraseña (RF-TEN-09): enlace de un solo uso que vence en 60 minutos.

El token de Django incluye el hash de la contraseña: deja de valer al cambiarla
(un solo uso) y vence según PASSWORD_RESET_TIMEOUT.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from shared.infrastructure.correo import encolar_correo
from tenancy.infrastructure.models import Usuario

AVISO = "Si el email está registrado, te enviamos un enlace para recuperar tu contraseña."
INVALIDO = "El enlace no es válido o ya venció. Pide uno nuevo."


class PedirEnlaceForm(forms.Form):
    email = forms.EmailField(label="Email")


def pedir_enlace(request):
    form = PedirEnlaceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = Usuario.objects.filter(
            email__iexact=form.cleaned_data["email"], is_active=True, es_tecnico=False
        ).first()
        if usuario:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)
            enlace = request.build_absolute_uri(f"/password-reset/{uid}/{token}/")
            with transaction.atomic():
                encolar_correo(
                    usuario.email,
                    "Recupera tu contraseña de Illumi",
                    f"Para definir una nueva contraseña abre este enlace:\n{enlace}\n\n"
                    "El enlace se puede usar una sola vez y vence en 60 minutos.",
                    usuario.empresa_id,
                )
        messages.info(request, AVISO)
        return redirect("login")
    return render(request, "tenancy/recuperar.html", {"form": form})


def definir_contrasena(request, uidb64, token):
    try:
        usuario = Usuario.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (ValueError, Usuario.DoesNotExist):
        usuario = None
    if usuario is None or not default_token_generator.check_token(usuario, token):
        return render(request, "tenancy/recuperar.html", {"error": INVALIDO})
    form = SetPasswordForm(usuario, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.info(request, "Tu contraseña fue actualizada. Ya puedes iniciar sesión.")
        return redirect("login")
    return render(request, "tenancy/recuperar.html", {"form": form, "nueva": True})
