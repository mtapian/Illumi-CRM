"""Configurar datos de la empresa (UC-TEN-04; RF-TEN-15 a 17)."""

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from shared.domain.tenant import empresa_actual
from tenancy.application.puertos import EmpresasRepo, ParametrosRepo
from tenancy.domain.errores import IgvInvalido
from tenancy.domain.igv import validar_igv


@dataclass(frozen=True)
class DatosEmpresa:
    """Datos editables. El RUC no está: no se edita después del registro (RF-TEN-17)."""

    razon_social: str
    nombre_comercial: str = ""
    direccion_fiscal: str = ""
    ubigeo: str = ""
    telefono: str = ""
    email: str = ""


class ActualizarEmpresa:
    def __init__(self, empresas: EmpresasRepo):
        self._empresas = empresas

    def ejecutar(self, datos: DatosEmpresa) -> None:
        self._empresas.actualizar(empresa_actual(), asdict(datos))


class CambiarIgv:
    """Registra un IGV nuevo con su fecha de vigencia; nunca edita los anteriores (RN-TEN-07)."""

    def __init__(self, parametros: ParametrosRepo):
        self._parametros = parametros

    def ejecutar(self, pct: Decimal, vigente_desde: date, hoy: date) -> None:
        validar_igv(pct)
        if vigente_desde < hoy:
            raise IgvInvalido("La fecha de vigencia del IGV no puede ser anterior a hoy")
        empresa_id = empresa_actual()
        fechas = {desde for desde, _ in self._parametros.historial("igv_pct", empresa_id)}
        if vigente_desde in fechas:
            raise IgvInvalido("Ya hay un cambio de IGV registrado para esa fecha")
        self._parametros.agregar("igv_pct", empresa_id, pct, vigente_desde)
