"""T18 (RF-TEN-09; art. 7.4): el correo se registra en la transacción y se envía fuera."""

import pytest
from django.core import mail
from django.core.management import call_command
from django.db import transaction

from shared.infrastructure.correo import encolar_correo
from shared.infrastructure.models import Correo

pytestmark = pytest.mark.django_db


def test_un_correo_de_una_transaccion_revertida_no_existe():
    with pytest.raises(RuntimeError), transaction.atomic():
        encolar_correo("lucia@andina.pe", "Asunto", "Cuerpo")
        raise RuntimeError("falla el caso de uso")
    assert not Correo.objects.exists()


def test_el_comando_envia_los_pendientes_y_los_marca_enviados(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    encolar_correo("lucia@andina.pe", "Recupera tu contraseña", "Enlace: …")
    call_command("enviar_correos")
    correo = Correo.objects.get()
    assert correo.estado == "ENVIADO" and correo.enviado_en is not None
    assert [m.to for m in mail.outbox] == [["lucia@andina.pe"]]
    call_command("enviar_correos")
    assert len(mail.outbox) == 1  # no se reenvía


def test_un_error_de_envio_queda_registrado_para_reintentar(settings):
    settings.EMAIL_BACKEND = "tests.shared.integration.backend_que_falla.Backend"
    encolar_correo("lucia@andina.pe", "Asunto", "Cuerpo")
    call_command("enviar_correos")
    correo = Correo.objects.get()
    assert correo.estado == "PENDIENTE" and correo.intentos == 1
