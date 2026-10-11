"""RF-TEN-16 (RN-TEN-07): los parámetros tributarios se aplican según su fecha de vigencia."""

from datetime import date
from decimal import Decimal

import pytest

from shared.domain.vigencia import SinValorVigente, valor_vigente
from tenancy.domain.errores import IgvInvalido
from tenancy.domain.igv import validar_igv

HISTORIAL = [(date(2011, 3, 1), Decimal("18")), (date(2027, 1, 1), Decimal("10"))]


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        (date(2026, 12, 31), Decimal("18")),  # el día antes del cambio
        (date(2027, 1, 1), Decimal("10")),  # el mismo día
        (date(2027, 1, 2), Decimal("10")),  # el día después
    ],
)
def test_valor_vigente_respeta_la_fecha(fecha, esperado):
    assert valor_vigente(HISTORIAL, fecha) == esperado


def test_el_orden_del_historial_no_importa():
    assert valor_vigente(list(reversed(HISTORIAL)), date(2026, 6, 1)) == Decimal("18")


def test_antes_del_primer_valor_no_hay_vigente():
    with pytest.raises(SinValorVigente):
        valor_vigente(HISTORIAL, date(2000, 1, 1))


@pytest.mark.parametrize("pct", ["0", "18", "18.5", "100", "0.01"])
def test_igv_valido(pct):
    assert validar_igv(Decimal(pct)) == Decimal(pct)


@pytest.mark.parametrize("pct", ["-1", "100.01", "100.001", "18.001"])
def test_igv_invalido(pct):
    with pytest.raises(IgvInvalido):
        validar_igv(Decimal(pct))
