"""T19 (RF-TEN-09): enlace de un solo uso que vence en 60 minutos."""

import re
from datetime import datetime, timedelta

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail

from shared.infrastructure.correo import enviar_pendientes
from tenancy.infrastructure.models import Usuario

pytestmark = pytest.mark.django_db


def pedir_enlace(client, email):
    client.post("/password-reset/", {"email": email})
    enviar_pendientes()
    return re.search(r"(/password-reset/\S+/)", mail.outbox[-1].body).group(1)


def test_el_enlace_vence_a_los_60_minutos(client, crear_empresa, monkeypatch):
    Usuario.objects.create_user(
        "ana@andina.pe", "Clave-Segura-2026", nombre="Ana", empresa=crear_empresa()
    )
    enlace = pedir_enlace(client, "ana@andina.pe")
    assert "Nueva contraseña" in client.get(enlace).content.decode()
    monkeypatch.setattr(
        default_token_generator, "_now", lambda: datetime.now() + timedelta(minutes=61)
    )
    assert "El enlace no es válido o ya venció" in client.get(enlace).content.decode()


def test_un_email_desconocido_no_revela_nada(client):
    respuesta = client.post("/password-reset/", {"email": "nadie@andina.pe"}, follow=True)
    assert "Si el email está registrado" in respuesta.content.decode()
    enviar_pendientes()
    assert mail.outbox == []
