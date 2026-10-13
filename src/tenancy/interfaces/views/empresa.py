"""Configurar datos de la empresa (UC-TEN-04; RF-TEN-17). El IGV pasó a los impuestos del
catálogo (0002e, ajusta RF-TEN-15 y 16).

El permiso `core.empresa.gestionar` se exige cuando exista la autorización de 0001c.
"""

from django.contrib import messages
from django.shortcuts import redirect, render

from tenancy.application.empresa import DatosEmpresa
from tenancy.infrastructure import contenedor
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.forms import EmpresaForm


@requiere("core.empresa.gestionar")
def configurar_empresa(request):
    empresa = request.user.empresa
    accion = request.POST.get("accion")
    datos_iniciales = {c: getattr(empresa, c) for c in EmpresaForm.base_fields if c != "logo"}
    form = EmpresaForm(
        request.POST if accion == "datos" else None,
        request.FILES if accion == "datos" else None,
        initial=datos_iniciales,
    )
    if accion == "datos" and form.is_valid():
        logo = form.cleaned_data.pop("logo")
        contenedor.actualizar_empresa().ejecutar(DatosEmpresa(**form.cleaned_data))
        if logo:
            empresa.logo = logo  # el archivo se guarda en el almacenamiento de medios
            empresa.save(update_fields=["logo"])
        messages.success(request, "Datos de la empresa actualizados")
        return redirect("configurar_empresa")
    return render(request, "tenancy/empresa.html", {"empresa": empresa, "form": form})
