"""Estado de la prueba o la suscripción de una empresa (RF-TEN-05, 18 a 20).

La fecha de término es inclusiva: la empresa opera hasta el final de ese día y queda
vencida desde el día siguiente. Todas las funciones reciben `hoy` (hora de Lima).
"""

from datetime import date, timedelta
from enum import StrEnum

DIAS_AVISO = 7


class Estado(StrEnum):
    TRIAL = "TRIAL"
    ACTIVA = "ACTIVA"
    VENCIDA = "VENCIDA"
    SUSPENDIDA = "SUSPENDIDA"


def estado_suscripcion(estado: Estado, fecha_termino: date | None, hoy: date) -> Estado:
    if estado == Estado.SUSPENDIDA:
        return Estado.SUSPENDIDA
    if fecha_termino is not None and hoy > fecha_termino:
        return Estado.VENCIDA
    return estado


def puede_operar(estado: Estado, fecha_termino: date | None, hoy: date) -> bool:
    return estado_suscripcion(estado, fecha_termino, hoy) in (Estado.TRIAL, Estado.ACTIVA)


def dias_para_vencer(fecha_termino: date | None, hoy: date) -> int | None:
    return None if fecha_termino is None else (fecha_termino - hoy).days


def mostrar_aviso_vencimiento(fecha_termino: date | None, hoy: date) -> bool:
    dias = dias_para_vencer(fecha_termino, hoy)
    return dias is not None and 0 <= dias <= DIAS_AVISO


def fecha_termino_prueba(fecha_registro: date, dias_prueba: int) -> date:
    return fecha_registro + timedelta(days=dias_prueba)


def texto_aviso(estado: Estado, dias: int) -> str:
    if estado == Estado.TRIAL:
        if dias == 0:
            return "Tu prueba vence hoy"
        return f"Te queda{'' if dias == 1 else 'n'} {dias} día{'' if dias == 1 else 's'} de prueba"
    if dias == 0:
        return "Tu suscripción vence hoy"
    return f"Tu suscripción vence en {dias} día{'' if dias == 1 else 's'}"
