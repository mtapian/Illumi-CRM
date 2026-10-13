"""RF-TEN-03 (RN-TEN-03) y RF-COM-01: RUC de 11 dígitos, prefijo 10/15/17/20 y dígito
verificador módulo 11; DNI de 8 dígitos. 0006a, T1: reglas de documento del maestro (RF-VEN-02,
49): las genéricas son datos; la especial del RUC (prefijo y dígito verificador) es código."""

import pytest

from shared.domain.documentos import TIPOS_INICIALES, Ruc, validar_numero
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


TIPOS = {t.abreviatura: t for t in TIPOS_INICIALES}


def test_tipos_iniciales_del_catalogo_06():
    assert {(t.abreviatura, t.codigo_sunat) for t in TIPOS_INICIALES} == {
        ("SD", "0"),
        ("DNI", "1"),
        ("CE", "4"),
        ("RUC", "6"),
        ("PAS", "7"),
    }


@pytest.mark.parametrize(
    "tipo, numero, limpio",
    [
        ("DNI", " 45871236 ", "45871236"),
        ("RUC", "20512345671", "20512345671"),
        ("CE", "ab12345", "AB12345"),
        ("PAS", "x1234567", "X1234567"),
        ("SD", "", ""),
    ],
)
def test_numeros_validos(tipo, numero, limpio):
    assert validar_numero(TIPOS[tipo], numero) == limpio


@pytest.mark.parametrize(
    "tipo, numero, mensaje",
    [
        ("DNI", "4587123", "El DNI debe tener 8 dígitos"),
        ("DNI", "4587123A", "El DNI debe tener 8 dígitos"),
        ("RUC", "20512345670", "El RUC no es válido"),
        ("RUC", "30512345671", "El RUC debe empezar con 10, 15, 17 o 20"),
        ("CE", "AB-123", "El Carné de extranjería solo admite letras y números"),
        ("CE", "A" * 13, "El Carné de extranjería debe tener de 1 a 12 letras o números"),
        ("PAS", "", "El número de Pasaporte es obligatorio"),
        ("SD", "123", "Sin documento no lleva número"),
    ],
)
def test_numeros_invalidos(tipo, numero, mensaje):
    with pytest.raises(DocumentoInvalido, match=mensaje):
        validar_numero(TIPOS[tipo], numero)
