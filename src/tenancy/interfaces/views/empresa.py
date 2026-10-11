"""Configurar datos de la empresa (UC-TEN-04; RF-TEN-15 a 17).

El permiso `core.empresa.gestionar` se exige cuando exista la autorización de 0001c.
"""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from shared.domain.errores import DomainError
from tenancy.application.empresa import DatosEmpresa
from tenancy.infrastructure import contenedor
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.forms import EmpresaForm, IgvForm


@requiere("core.empresa.gestionar")
def configurar_empresa(request):
    empresa = request.user.empresa
    hoy = timezone.localdate()
    accion = request.POST.get("accion")
    datos_iniciales = {c: getattr(empresa, c) for c in EmpresaForm.base_fields if c != "logo"}
    form = EmpresaForm(
        request.POST if accion == "datos" else None,
        request.FILES if accion == "datos" else None,
        initial=datos_iniciales,
    )
    form_igv = IgvForm(
        request.POST if accion == "igv" else None,
        initial={"igv_pct": contenedor.tenancy_service().igv_vigente(hoy), "vigente_desde": hoy},
    )
    if accion == "datos" and form.is_valid():
        logo = form.cleaned_data.pop("logo")
        contenedor.actualizar_empresa().ejecutar(DatosEmpresa(**form.cleaned_data))
        if logo:
            empresa.logo = logo  # el archivo se guarda en el almacenamiento de medios
            empresa.save(update_fields=["logo"])
        messages.success(request, "Datos de la empresa actualizados")
        return redirect("configurar_empresa")
    if accion == "igv" and form_igv.is_valid():
        try:
            contenedor.cambiar_igv().ejecutar(
                form_igv.cleaned_data["igv_pct"], form_igv.cleaned_data["vigente_desde"], hoy
            )
        except DomainError as e:
            form_igv.add_error(None, e.mensaje)
        else:
            messages.success(request, "IGV registrado con su fecha de vigencia")
            return redirect("configurar_empresa")
    return render(
        request, "tenancy/empresa.html", {"empresa": empresa, "form": form, "form_igv": form_igv}
    )
