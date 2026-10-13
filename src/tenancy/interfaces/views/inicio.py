from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.formats import date_format

from shared.interfaces.avisos import avisos
from shared.interfaces.tablero import paneles, tarjetas


@login_required
def dashboard(request):
    """Inicio (0008c, RF-FIN-14, 17 a 24): tarjetas, avisos y paneles que registran los
    contextos, cada uno con su permiso."""
    hoy = date_format(timezone.localdate(), "j F Y")
    return render(
        request,
        "tenancy/dashboard.html",
        {
            "primeros_pasos": request.session.get("primeros_pasos", False),
            "tarjetas": tarjetas.para(request),
            "avisos": avisos.para(request),
            "paneles": paneles.para(request),
            "migas": [("Inicio", "/"), ("Panel principal", None), (hoy, None)],
        },
    )
