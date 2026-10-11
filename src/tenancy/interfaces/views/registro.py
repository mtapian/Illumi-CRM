"""Registro de empresa con prueba gratis (UC-TEN-01)."""

import logging

from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils import timezone

from shared.domain.errores import DocumentoInvalido, DomainError
from tenancy.application.registro import DatosRegistro
from tenancy.domain.errores import EmailDuplicado, RucDuplicado
from tenancy.infrastructure import contenedor
from tenancy.infrastructure.models import Usuario
from tenancy.interfaces.forms import RegistroForm

logger = logging.getLogger(__name__)
CAMPO_DEL_ERROR = {DocumentoInvalido: "ruc", RucDuplicado: "ruc", EmailDuplicado: "email"}


def registro(request):
    form = RegistroForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            resultado = contenedor.registrar_empresa().ejecutar(
                DatosRegistro(**form.cleaned_data), timezone.localdate()
            )
        except DomainError as e:
            form.add_error(CAMPO_DEL_ERROR.get(type(e)), e.mensaje)
        except Exception:
            logger.exception("Falló el registro de una empresa")
            error = "No pudimos completar el registro. Inténtalo de nuevo."
        else:
            admin = Usuario.objects.get(pk=resultado.admin_id)
            login(request, admin, backend="tenancy.infrastructure.auth_backend.EmailBackend")
            request.session["primeros_pasos"] = True
            return redirect("dashboard")
    return render(request, "tenancy/registro.html", {"form": form, "error": error})
