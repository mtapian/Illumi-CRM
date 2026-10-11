"""RF-TEN-03 (RN-TEN-03) y RF-COM-01: RUC de 11 dígitos, prefijo 10/15/17/20 y dígito
verificador módulo 11; DNI de 8 dígitos."""

import pytest

from shared.domain.documentos import Ruc, validar_documento
from shared.domain.errores import DocumentoInvalido


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
    with pytest.raises(DocumentoInvalido, match=mensaje):
        Ruc.validar(valor)


def test_espacios_alrededor_se_ignoran():
    assert Ruc.validar(" 20601234565 ").valor == "20601234565"


def test_dni_de_8_digitos():
    assert validar_documento("DNI", " 45678912 ") == "45678912"
    for malo in ("1234567", "123456789", "1234567A"):
        with pytest.raises(DocumentoInvalido, match="El DNI debe tener 8 dígitos"):
            validar_documento("DNI", malo)


def test_documento_ruc_o_dni():
    assert validar_documento("RUC", "20512345671") == "20512345671"
    with pytest.raises(DocumentoInvalido, match="El tipo de documento debe ser RUC o DNI"):
        validar_documento("CE", "123")
