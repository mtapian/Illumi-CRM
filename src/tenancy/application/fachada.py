"""Fachada pública de tenancy para los demás contextos (planes 0001a y 0001b §1)."""

from datetime import date
from decimal import Decimal

from shared.domain.tenant import empresa_actual
from shared.domain.vigencia import SinValorVigente, valor_vigente
from tenancy.application.puertos import EmpresasRepo, HabilitacionesRepo, ParametrosRepo
from tenancy.domain.habilitaciones import habilitaciones_efectivas
from tenancy.domain.suscripcion import puede_operar


class TenancyService:
    def __init__(
        self, parametros: ParametrosRepo, empresas: EmpresasRepo, habilitaciones: HabilitacionesRepo
    ):
        self._parametros = parametros
        self._empresas = empresas
        self._habilitaciones = habilitaciones

    def parametro_vigente(self, clave: str, fecha: date) -> Decimal:
        """Valor propio de la empresa actual si tiene uno vigente; si no, el de la plataforma."""
        try:
            return valor_vigente(self._parametros.historial(clave, empresa_actual()), fecha)
        except SinValorVigente:
            return valor_vigente(self._parametros.historial(clave, None), fecha)

    def igv_vigente(self, fecha: date) -> Decimal:
        return self.parametro_vigente("igv_pct", fecha)

    def empresa_activa(self, empresa_id: int, hoy: date) -> bool:
        estado, fecha_termino = self._empresas.estado(empresa_id)
        return puede_operar(estado, fecha_termino, hoy)

    def habilitaciones_de(self, empresa_id: int, hoy: date) -> frozenset[str]:
        """Códigos de funcionalidad habilitados hoy: plan ± ajustes vigentes (RF-TEN-23, 30)."""
        return habilitaciones_efectivas(
            self._habilitaciones.funcionalidades_plan(empresa_id),
            self._habilitaciones.ajustes(empresa_id),
            hoy,
        )

    def limite_productos(self, empresa_id: int) -> int | None:
        """Productos activos que permite el plan; None es ilimitado (RF-CAT-10)."""
        return self._empresas.limite_productos(empresa_id)
