"""RUC peruano (RF-TEN-03, RN-TEN-03)."""

from dataclasses import dataclass

from tenancy.domain.errores import RucInvalido

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
            raise RucInvalido("El RUC debe tener 11 dígitos")
        if valor[:2] not in _PREFIJOS:
            raise RucInvalido("El RUC debe empezar con 10, 15, 17 o 20")
        if _digito_verificador(valor[:10]) != int(valor[10]):
            raise RucInvalido("El RUC no es válido")
        return cls(valor)
