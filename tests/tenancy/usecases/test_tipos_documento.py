"""0006a, T2: maestro de tipos de documento de la plataforma (RF-VEN-49; art. 10.4)."""

from dataclasses import replace

import pytest

from shared.domain.documentos import ALFANUMERICO, ReglasDocumento, validar_numero
from shared.domain.errores import DocumentoInvalido
from tenancy.infrastructure.contenedor import guardar_tipo_documento, tenancy_service
from tenancy.infrastructure.models import TipoDocumento

pytestmark = pytest.mark.django_db
CEDULA = ReglasDocumento("CDI", "A", "Cédula diplomática", True, 1, 15, ALFANUMERICO)


def test_sembrados_y_leidos_por_la_fachada():
    activos = {t.abreviatura: t for t in tenancy_service().tipos_documento()}
    assert set(activos) == {"SD", "DNI", "CE", "RUC", "PAS"}
    assert activos["RUC"].validacion == "RUC"
    assert tenancy_service().reglas_documento("DNI").longitud_max == 8


def test_un_tipo_nuevo_valida_sin_tocar_el_codigo():
    id_ = guardar_tipo_documento().ejecutar(None, CEDULA)
    assert TipoDocumento.objects.get(pk=id_).codigo_sunat == "A"
    reglas = tenancy_service().reglas_documento("CDI")
    assert validar_numero(reglas, "ab1") == "AB1"
    with pytest.raises(DocumentoInvalido, match="solo admite letras y números"):
        validar_numero(reglas, "ab-1")


@pytest.mark.parametrize(
    "cambio, mensaje",
    [
        ({"abreviatura": "DNI"}, "Ya existe el tipo de documento DNI"),
        ({"codigo_sunat": "1"}, "Ya existe un tipo de documento con el código SUNAT 1"),
        ({"nombre": " "}, "El nombre es obligatorio"),
        ({"longitud_min": 5, "longitud_max": 2}, "La longitud mínima no puede superar la máxima"),
        ({"caracteres": "OTRO"}, "Caracteres no válidos"),
        ({"validacion": "OTRA"}, "Validación especial no válida"),
    ],
)
def test_tipo_invalido(cambio, mensaje):
    with pytest.raises(DocumentoInvalido, match=mensaje):
        guardar_tipo_documento().ejecutar(None, replace(CEDULA, **cambio))


def test_abreviatura_y_codigo_fijos_y_desactivar():
    dni = TipoDocumento.objects.get(abreviatura="DNI")
    reglas = tenancy_service().reglas_documento("DNI")
    with pytest.raises(DocumentoInvalido, match="La abreviatura y el código SUNAT no se cambian"):
        guardar_tipo_documento().ejecutar(dni.id, replace(reglas, codigo_sunat="9"))
    guardar_tipo_documento().ejecutar(dni.id, replace(reglas, nombre="DNI peruano", activo=False))
    assert "DNI" not in {t.abreviatura for t in tenancy_service().tipos_documento()}
    assert tenancy_service().reglas_documento("DNI").nombre == "DNI peruano"  # lo conserva
    sin_numero = replace(CEDULA, abreviatura="X", codigo_sunat="X", exige_numero=False)
    guardar_tipo_documento().ejecutar(None, sin_numero)
    x = TipoDocumento.objects.get(abreviatura="X")
    assert (x.longitud_min, x.longitud_max) == (0, 0)  # sin número: sin longitud
