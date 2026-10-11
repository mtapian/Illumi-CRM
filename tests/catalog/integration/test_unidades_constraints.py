"""T5, T6 y T8: unidades y constraints del catálogo (RF-CAT-01 a 03, 08, 12, 13)."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from catalog.application import productos as uc
from catalog.domain.errores import SkuDuplicado, UnidadInvalida
from catalog.domain.producto import DatosProducto
from catalog.infrastructure.contenedor import caso_de_uso
from catalog.infrastructure.models import Producto, Unidad
from shared.domain.tenant import tenant_context
from tenancy.application.registro import DatosRegistro
from tenancy.infrastructure.contenedor import registrar_empresa
from tenancy.infrastructure.models import Plan

pytestmark = pytest.mark.django_db


def test_al_registrar_una_empresa_se_crean_sus_unidades():
    Plan.objects.create(nombre="Prueba", slug="prueba", es_plan_prueba=True)
    datos = DatosRegistro("20601234565", "Andina", "", "Lucía", "l@a.pe", "Clave-Segura-2026")
    empresa_id = registrar_empresa().ejecutar(datos, date(2026, 10, 10)).empresa_id
    with tenant_context(empresa_id):
        codigos = dict(Unidad.objects.values_list("abreviatura", "codigo_sunat"))
    assert codigos == {"UND": "NIU", "KG": "KGM", "G": "GRM", "L": "LTR", "ML": "MLT"} | {
        "CAJA": "BX",  # enmienda 3
        "DOC": "DZN",
        "MT": "MTR",
        "PAQ": "PK",
        "SERV": "ZZ",
    }


def test_unidad_en_uso_no_se_elimina_ni_se_desactiva(empresa_catalogo):
    _, actor = empresa_catalogo
    caso_de_uso(uc.CrearProducto).ejecutar(actor, DatosProducto("INS-MALTA", "Malta", "BIEN", "KG"))
    kg = Unidad.objects.get(abreviatura="KG").id
    with pytest.raises(UnidadInvalida, match="La unidad está en uso; puedes desactivarla"):
        caso_de_uso(uc.EliminarUnidad).ejecutar(actor, kg)
    with pytest.raises(UnidadInvalida, match="productos activos"):
        caso_de_uso(uc.CambiarEstadoUnidad).ejecutar(actor, kg, False)
    ml = Unidad.objects.get(abreviatura="ML").id
    caso_de_uso(uc.EliminarUnidad).ejecutar(actor, ml)
    with pytest.raises(UnidadInvalida, match="Ya existe la unidad KG"):
        caso_de_uso(uc.CrearUnidad).ejecutar(actor, "Kilo", "kg", "KGM")


def test_sku_unico_por_empresa_y_checks_de_la_base(empresa_catalogo, crear_empresa):
    empresa, actor = empresa_catalogo
    crear = caso_de_uso(uc.CrearProducto)
    crear.ejecutar(actor, DatosProducto("INS-MALTA", "Malta", "BIEN", "KG"))
    with pytest.raises(SkuDuplicado, match="Ya existe un producto con el SKU INS-MALTA"):
        crear.ejecutar(actor, DatosProducto("ins-malta", "Otra", "BIEN", "KG"))
    kg = Unidad.objects.get(abreviatura="KG")
    for i, malo in enumerate(
        (
            {"tipo": "OTRO"},
            {"se_compra": False},  # RF-CAT-38: sin ninguna casilla
            {"precio_venta": 5},  # RF-CAT-39: precio sin "se vende"
            {"se_vende": True},  # se vende sin precio
            {"tipo": "SERVICIO", "se_fabrica": True},  # RF-CAT-37
            {"tipo": "SERVICIO", "peso_kg": 1},
            {"vida_util_dias": 0},
        )
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            Producto.objects.create(sku=f"X{i}", nombre="x", unidad=kg, **malo)
    otra = crear_empresa(ruc="20100047218")
    Unidad.all_tenants.create(empresa=otra, nombre="Kg", abreviatura="KG", codigo_sunat="KGM")
    Producto.all_tenants.create(
        empresa=otra,
        sku="INS-MALTA",
        nombre="Malta",
        unidad=Unidad.all_tenants.get(empresa=otra),
    )
    assert Producto.all_tenants.filter(sku="INS-MALTA").count() == 2
