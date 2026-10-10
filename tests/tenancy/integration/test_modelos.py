"""T10 y T11: restricciones de base de datos de tenancy (RF-TEN-04, 05, 06, 16, 17)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import authenticate
from django.db import DatabaseError, IntegrityError, transaction

from tenancy.infrastructure.models import Empresa, ParametroVigencia, Plan, Usuario

pytestmark = pytest.mark.django_db


def crear_plan(slug="negocio", **kw):
    return Plan.objects.create(nombre=slug.title(), slug=slug, **kw)


def crear_empresa(ruc="20601234565", **kw):
    return Empresa.objects.create(
        ruc=ruc, razon_social="Cervecería Andina S.A.C.", plan=crear_plan(f"p{ruc}"), **kw
    )


def test_ruc_unico():
    crear_empresa()
    with pytest.raises(IntegrityError), transaction.atomic():
        crear_empresa()


def test_el_ruc_no_se_puede_modificar_en_la_base_de_datos():
    empresa = crear_empresa()
    with pytest.raises(DatabaseError), transaction.atomic():
        Empresa.objects.filter(pk=empresa.pk).update(ruc="20512345671")


def test_un_solo_plan_de_prueba_activo():
    crear_plan("prueba", es_plan_prueba=True)
    crear_plan("viejo", es_plan_prueba=True, activo=False)
    with pytest.raises(IntegrityError), transaction.atomic():
        crear_plan("otro", es_plan_prueba=True)


def test_parametro_vigencia_es_solo_insercion():
    p = ParametroVigencia.objects.create(
        clave="umbral_boleta_identificada", valor=Decimal("700"), vigente_desde=date(2024, 1, 1)
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        ParametroVigencia.objects.filter(pk=p.pk).update(valor=Decimal("10"))
    with pytest.raises(DatabaseError), transaction.atomic():
        ParametroVigencia.objects.filter(pk=p.pk).delete()


def test_un_valor_por_ambito_clave_y_fecha():
    ParametroVigencia.objects.create(
        clave="umbral_boleta_identificada", valor=Decimal("700"), vigente_desde=date(2024, 1, 1)
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ParametroVigencia.objects.create(
            clave="umbral_boleta_identificada", valor=Decimal("800"), vigente_desde=date(2024, 1, 1)
        )


def test_email_unico_sin_distinguir_mayusculas():
    Usuario.objects.create_user("lucia@andina.pe", "Clave-Segura-2026", nombre="Lucía")
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.create_user("LUCIA@andina.pe", "otra-clave-123", nombre="Otra")


def test_usuario_normal_se_autentica_y_el_tecnico_no():
    Usuario.objects.create_user("lucia@andina.pe", "Clave-Segura-2026", nombre="Lucía")
    Usuario.objects.create_user("n8n@andina.pe", "Clave-Segura-2026", nombre="n8n", es_tecnico=True)
    assert authenticate(email="lucia@andina.pe", password="Clave-Segura-2026") is not None
    assert authenticate(email="n8n@andina.pe", password="Clave-Segura-2026") is None
