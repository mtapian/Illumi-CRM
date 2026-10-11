"""Documentos de identidad peruanos: RUC (RF-TEN-03, RN-TEN-03) y DNI (RF-COM-01)."""

from dataclasses import dataclass

from shared.domain.errores import DocumentoInvalido

_PREFIJOS = ("10", "15", "17", "20")
_PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _digito_verificador(primeros_diez: str) -> int:
    resto = 11 - sum(int(d) * p for d, p in zip(primeros_diez, _PESOS, strict=True)) % 11
    return {10: 0, 11: 1}.get(resto, resto)


@dataclass(frozen=True)
class Ruc:
    valor: str

    @classmethod
    def validar(cls, texto: str) -> "Ruc":
        valor = texto.strip()
        if len(valor) != 11 or not valor.isdigit():
            raise DocumentoInvalido("El RUC debe tener 11 dígitos")
        if valor[:2] not in _PREFIJOS:
            raise DocumentoInvalido("El RUC debe empezar con 10, 15, 17 o 20")
        if _digito_verificador(valor[:10]) != int(valor[10]):
            raise DocumentoInvalido("El RUC no es válido")
        return cls(valor)


TIPOS = ("RUC", "DNI")


def validar_documento(tipo: str, numero: str) -> str:
    """Devuelve el número limpio o rechaza el documento."""
    if tipo not in TIPOS:
        raise DocumentoInvalido("El tipo de documento debe ser RUC o DNI")
    if tipo == "RUC":
        return Ruc.validar(numero).valor
    numero = numero.strip()
    if len(numero) != 8 or not numero.isdigit():
        raise DocumentoInvalido("El DNI debe tener 8 dígitos")
    return numero
