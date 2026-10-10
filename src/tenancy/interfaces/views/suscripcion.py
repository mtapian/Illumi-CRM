from django.shortcuts import render
from django.utils import timezone

from tenancy.domain.suscripcion import estado_suscripcion, puede_operar
from tenancy.interfaces.acceso import requiere


@requiere("core.suscripcion.ver")
def suscripcion(request):
    """Plan, vencimiento y uso de la empresa (RF-TEN-18), solo lectura."""
    empresa = request.user.empresa
    hoy = timezone.localdate()
    return render(
        request,
        "tenancy/suscripcion.html",
        {
            "empresa": empresa,
            "estado": estado_suscripcion(empresa.estado, empresa.fecha_termino, hoy),
            "puede_operar": puede_operar(empresa.estado, empresa.fecha_termino, hoy),
            "usuarios_activos": empresa.usuarios.filter(is_active=True, es_tecnico=False).count(),
        },
    )
