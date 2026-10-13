"""Documentos de identidad: RUC (RF-TEN-03, RN-TEN-03), DNI (RF-COM-01) y las reglas de cada
tipo del maestro de la plataforma (0006a, RF-VEN-49; constitución, art. 10.4): longitud y
caracteres son datos; la validación especial del RUC es código."""

from dataclasses import dataclass, replace

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


DIGITOS, ALFANUMERICO = "DIGITOS", "ALFANUMERICO"
NINGUNA, VALIDACION_RUC = "NINGUNA", "RUC"


@dataclass(frozen=True)
class ReglasDocumento:
    """Un tipo de documento del maestro (catálogo 06 de SUNAT)."""

    abreviatura: str
    codigo_sunat: str
    nombre: str
    exige_numero: bool = True
    longitud_min: int = 1
    longitud_max: int = 15
    caracteres: str = ALFANUMERICO
    validacion: str = NINGUNA
    activo: bool = True


# Se siembran en el maestro (RF-VEN-49); luego el super admin los mantiene.
TIPOS_INICIALES = (
    ReglasDocumento("SD", "0", "Sin documento", False, 0, 0),
    ReglasDocumento("DNI", "1", "DNI", True, 8, 8, DIGITOS),
    ReglasDocumento("CE", "4", "Carné de extranjería", True, 1, 12),
    ReglasDocumento("RUC", "6", "RUC", True, 11, 11, DIGITOS, VALIDACION_RUC),
    ReglasDocumento("PAS", "7", "Pasaporte", True, 1, 12),
)


def validar_numero(reglas: ReglasDocumento, numero: str) -> str:
    """RF-VEN-02: devuelve el número limpio (sin espacios, en mayúsculas) o lo rechaza."""
    numero = numero.strip().upper()
    if not reglas.exige_numero:
        if numero:
            raise DocumentoInvalido(f"{reglas.nombre} no lleva número")
        return ""
    if not numero:
        raise DocumentoInvalido(f"El número de {reglas.nombre} es obligatorio")
    if reglas.validacion == VALIDACION_RUC:
        return Ruc.validar(numero).valor
    unidad = "dígitos" if reglas.caracteres == DIGITOS else "letras o números"
    largo = (
        f"{reglas.longitud_min}"
        if reglas.longitud_min == reglas.longitud_max
        else f"de {reglas.longitud_min} a {reglas.longitud_max}"
    )
    fuera_de_rango = not reglas.longitud_min <= len(numero) <= reglas.longitud_max
    if reglas.caracteres == DIGITOS and (fuera_de_rango or not numero.isdigit()):
        raise DocumentoInvalido(f"El {reglas.nombre} debe tener {largo} {unidad}")
    if reglas.caracteres == ALFANUMERICO and not (numero.isascii() and numero.isalnum()):
        raise DocumentoInvalido(f"El {reglas.nombre} solo admite letras y números")
    if fuera_de_rango:
        raise DocumentoInvalido(f"El {reglas.nombre} debe tener {largo} {unidad}")
    return numero


def validar_reglas(r: ReglasDocumento) -> ReglasDocumento:
    """RF-VEN-49: un tipo del maestro bien definido; sin número, sin longitud."""
    r = replace(
        r,
        abreviatura=r.abreviatura.strip().upper(),
        codigo_sunat=r.codigo_sunat.strip().upper(),
        nombre=r.nombre.strip(),
    )
    if not r.abreviatura:
        raise DocumentoInvalido("La abreviatura es obligatoria", "abreviatura")
    if not r.codigo_sunat:
        raise DocumentoInvalido("El código SUNAT es obligatorio", "codigo_sunat")
    if not r.nombre:
        raise DocumentoInvalido("El nombre es obligatorio", "nombre")
    if r.caracteres not in (DIGITOS, ALFANUMERICO):
        raise DocumentoInvalido("Caracteres no válidos", "caracteres")
    if r.validacion not in (NINGUNA, VALIDACION_RUC):
        raise DocumentoInvalido("Validación especial no válida", "validacion")
    if not r.exige_numero:
        return replace(r, longitud_min=0, longitud_max=0, validacion=NINGUNA)
    if r.longitud_min < 1 or r.longitud_max > 20:
        raise DocumentoInvalido("La longitud debe estar entre 1 y 20", "longitud_min")
    if r.longitud_min > r.longitud_max:
        raise DocumentoInvalido("La longitud mínima no puede superar la máxima", "longitud_min")
    return r
