"""T21: datos de la empresa e IGV con vigencia (RF-TEN-15 a 17; RN-TEN-07)."""

import dataclasses
from datetime import date, timedelta
from decimal import Decimal

import pytest

from shared.domain.tenant import tenant_context
from tenancy.application.empresa import DatosEmpresa
from tenancy.domain.errores import IgvInvalido
from tenancy.infrastructure.contenedor import actualizar_empresa, cambiar_igv, tenancy_service
from tenancy.infrastructure.models import Empresa

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


@pytest.fixture
def empresa(crear_empresa):
    return crear_empresa()


def test_actualiza_los_datos_pero_el_ruc_no_es_un_dato_editable(empresa):
    assert "ruc" not in {f.name for f in dataclasses.fields(DatosEmpresa)}
    with tenant_context(empresa.id):
        actualizar_empresa().ejecutar(
            DatosEmpresa(razon_social="Andina S.A.C.", nombre_comercial="Andina Brewing")
        )
    empresa.refresh_from_db()
    assert (empresa.nombre_comercial, empresa.ruc) == ("Andina Brewing", "20601234565")


def test_el_igv_cambiado_desde_manana_no_afecta_hoy(empresa):
    with tenant_context(empresa.id):
        cambiar_igv().ejecutar(Decimal("10"), HOY + timedelta(days=1), HOY)
        assert tenancy_service().igv_vigente(HOY) == Decimal("18")
        assert tenancy_service().igv_vigente(HOY + timedelta(days=1)) == Decimal("10")


def test_no_se_cambia_el_igv_hacia_atras(empresa):
    with tenant_context(empresa.id), pytest.raises(IgvInvalido, match="no puede ser anterior"):
        cambiar_igv().ejecutar(Decimal("10"), HOY - timedelta(days=1), HOY)


def test_igv_fuera_de_rango(empresa):
    with tenant_context(empresa.id), pytest.raises(IgvInvalido):
        cambiar_igv().ejecutar(Decimal("100.5"), HOY, HOY)


def test_dos_cambios_el_mismo_dia_se_rechazan(empresa):
    with tenant_context(empresa.id):
        cambiar_igv().ejecutar(Decimal("10"), HOY, HOY)
        with pytest.raises(IgvInvalido, match="Ya hay un cambio"):
            cambiar_igv().ejecutar(Decimal("12"), HOY, HOY)
    assert Empresa.objects.count() == 1
