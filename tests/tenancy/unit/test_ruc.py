"""RF-TEN-03 (RN-TEN-03): RUC de 11 dígitos, prefijo 10/15/17/20 y dígito verificador módulo 11."""

import pytest

from tenancy.domain.errores import RucInvalido
from tenancy.domain.ruc import Ruc


@pytest.mark.parametrize("valor", ["20601234565", "20512345671", "10456789124"])
def test_ruc_valido(valor):
    assert Ruc.validar(valor).valor == valor


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [
        ("2060123456", "El RUC debe tener 11 dígitos"),
        ("2060123456A", "El RUC debe tener 11 dígitos"),
        ("30601234567", "El RUC debe empezar con 10, 15, 17 o 20"),
        ("20601234560", "El RUC no es válido"),
    ],
)
def test_ruc_invalido(valor, mensaje):
    with pytest.raises(RucInvalido, match=mensaje):
        Ruc.validar(valor)


def test_espacios_alrededor_se_ignoran():
    assert Ruc.validar(" 20601234565 ").valor == "20601234565"
