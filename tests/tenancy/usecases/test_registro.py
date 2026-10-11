"""T14: RegistrarEmpresa (RF-TEN-01 a 05; RN-TEN-01 a 03)."""

from datetime import date

import pytest

from shared.domain.errores import DocumentoInvalido
from tenancy.application.registro import DatosRegistro, RegistrarEmpresa
from tenancy.application.sembradores import RegistroSembradores
from tenancy.domain.errores import EmailDuplicado, RucDuplicado
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.contenedor import registrar_empresa
from tenancy.infrastructure.models import Empresa, Plan, Usuario

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 10)


@pytest.fixture(autouse=True)
def plan_de_prueba(db):
    return Plan.objects.create(
        nombre="Negocio", slug="negocio", es_plan_prueba=True, dias_prueba=14
    )


def datos(**kw):
    base = dict(
        ruc="20601234565",
        razon_social="Cervecería Andina S.A.C.",
        nombre_comercial="",
        nombre="Lucía Torres",
        email="lucia@andina.pe",
        password="Clave-Segura-2026",
    )
    return DatosRegistro(**(base | kw))


def caso(sembradores=None) -> RegistrarEmpresa:
    return registrar_empresa(sembradores or RegistroSembradores())


def test_crea_empresa_en_prueba_con_su_administrador():
    resultado = caso().ejecutar(datos(), HOY)
    empresa = Empresa.objects.get(pk=resultado.empresa_id)
    admin = Usuario.objects.get(pk=resultado.admin_id)
    assert empresa.estado == Estado.TRIAL
    assert empresa.fecha_termino == date(2026, 10, 24)
    assert admin.empresa_id == empresa.id and admin.is_active
    assert admin.check_password("Clave-Segura-2026")


def test_ejecuta_los_sembradores_con_la_empresa_nueva():
    vistos = []
    registro = RegistroSembradores()
    registro.registrar(lambda empresa, admin, hoy: vistos.append((empresa, admin, hoy)))
    resultado = caso(registro).ejecutar(datos(), HOY)
    assert vistos == [(resultado.empresa_id, resultado.admin_id, HOY)]


def test_ruc_invalido_no_crea_nada():
    with pytest.raises(DocumentoInvalido):
        caso().ejecutar(datos(ruc="20601234560"), HOY)
    assert not Empresa.objects.exists() and not Usuario.objects.exists()


def test_ruc_duplicado():
    caso().ejecutar(datos(), HOY)
    with pytest.raises(RucDuplicado, match="Ya existe una empresa con este RUC"):
        caso().ejecutar(datos(email="otra@andina.pe"), HOY)


def test_email_duplicado_sin_distinguir_mayusculas():
    caso().ejecutar(datos(), HOY)
    with pytest.raises(EmailDuplicado, match="Este email ya está registrado"):
        caso().ejecutar(datos(ruc="20512345671", email="LUCIA@andina.pe"), HOY)
    assert Empresa.objects.count() == 1


def test_si_un_sembrador_falla_no_queda_nada():
    def falla(empresa, admin, hoy):
        raise RuntimeError("no se pudo crear el almacén")

    registro = RegistroSembradores()
    registro.registrar(falla)
    with pytest.raises(RuntimeError):
        caso(registro).ejecutar(datos(), HOY)
    assert not Empresa.objects.exists() and not Usuario.objects.exists()


def test_doble_envio_crea_una_sola_empresa():
    caso().ejecutar(datos(), HOY)
    with pytest.raises((RucDuplicado, EmailDuplicado)):
        caso().ejecutar(datos(), HOY)
    assert Empresa.objects.count() == 1 and Usuario.objects.count() == 1
