"""T12: TenancyService (RF-TEN-16: IGV con vigencia; RF-TEN-18: empresa que puede operar)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from shared.domain.tenant import tenant_context
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.contenedor import tenancy_service
from tenancy.infrastructure.models import ParametroVigencia

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


def test_igv_de_la_plataforma_y_cambio_propio_de_la_empresa(crear_empresa):
    a, b = crear_empresa("20601234565"), crear_empresa("20512345671")
    ParametroVigencia.objects.create(
        empresa=a, clave="igv_pct", valor=10, vigente_desde=date(2027, 1, 1)
    )
    servicio = tenancy_service()
    with tenant_context(a.id):
        assert servicio.igv_vigente(date(2026, 12, 31)) == Decimal("18")
        assert servicio.igv_vigente(date(2027, 1, 1)) == Decimal("10")
    with tenant_context(b.id):
        assert servicio.igv_vigente(date(2027, 1, 1)) == Decimal("18")


def test_empresa_activa_usa_el_estado_de_la_suscripcion(crear_empresa):
    vigente = crear_empresa("20601234565", fecha_termino=HOY)
    vencida = crear_empresa("20512345671", fecha_termino=HOY - timedelta(days=1))
    suspendida = crear_empresa("10456789124", estado=Estado.SUSPENDIDA, fecha_termino=HOY)
    servicio = tenancy_service()
    assert servicio.empresa_activa(vigente.id, HOY) is True
    assert servicio.empresa_activa(vencida.id, HOY) is False
    assert servicio.empresa_activa(suspendida.id, HOY) is False
