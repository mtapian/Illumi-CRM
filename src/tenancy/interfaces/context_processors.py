from django.utils import timezone

from tenancy.domain.suscripcion import (
    Estado,
    dias_para_vencer,
    mostrar_aviso_vencimiento,
    texto_aviso,
)


def aviso_vencimiento(request):
    """Aviso en todas las páginas cuando faltan 7 días o menos (RF-TEN-19)."""
    empresa = getattr(getattr(request, "user", None), "empresa", None)
    hoy = timezone.localdate()
    if empresa is None or not mostrar_aviso_vencimiento(empresa.fecha_termino, hoy):
        return {}
    dias = dias_para_vencer(empresa.fecha_termino, hoy)
    return {"aviso_vencimiento": texto_aviso(Estado(empresa.estado), dias)}
