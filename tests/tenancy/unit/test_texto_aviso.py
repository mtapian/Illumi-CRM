"""T25 (RF-TEN-19): texto del aviso de vencimiento."""

import pytest

from tenancy.domain.suscripcion import Estado, texto_aviso


@pytest.mark.parametrize(
    ("estado", "dias", "texto"),
    [
        (Estado.TRIAL, 5, "Te quedan 5 días de prueba"),
        (Estado.TRIAL, 1, "Te queda 1 día de prueba"),
        (Estado.TRIAL, 0, "Tu prueba vence hoy"),
        (Estado.ACTIVA, 7, "Tu suscripción vence en 7 días"),
        (Estado.ACTIVA, 0, "Tu suscripción vence hoy"),
    ],
)
def test_texto_del_aviso(estado, dias, texto):
    assert texto_aviso(estado, dias) == texto
