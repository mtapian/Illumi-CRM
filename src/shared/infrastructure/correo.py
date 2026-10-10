"""Outbox de correos: se registran dentro de la transacción y se envían fuera (art. 7.4)."""

import logging

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from shared.infrastructure.models import Correo

logger = logging.getLogger(__name__)


def encolar_correo(destinatario: str, asunto: str, cuerpo: str, empresa_id: int | None = None):
    correo = Correo.objects.create(
        empresa_id=empresa_id, destinatario=destinatario, asunto=asunto, cuerpo=cuerpo
    )
    transaction.on_commit(lambda: enviar_pendientes([correo.id]))  # intento inmediato
    return correo


def enviar_pendientes(ids: list[int] | None = None) -> int:
    """Envía los correos pendientes; lo que falla queda pendiente para el cron."""
    enviados = 0
    with transaction.atomic():
        pendientes = Correo.objects.select_for_update(skip_locked=True).filter(estado="PENDIENTE")
        if ids is not None:
            pendientes = pendientes.filter(id__in=ids)
        for correo in pendientes:
            correo.intentos += 1
            try:
                send_mail(correo.asunto, correo.cuerpo, None, [correo.destinatario])
            except Exception:
                logger.exception("No se pudo enviar el correo %s", correo.id)
            else:
                correo.estado, correo.enviado_en = "ENVIADO", timezone.now()
                enviados += 1
            correo.save(update_fields=["intentos", "estado", "enviado_en"])
    return enviados
