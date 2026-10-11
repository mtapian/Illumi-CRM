"""Arma los casos de uso del catálogo con sus adaptadores reales."""

from datetime import date

from django.db import transaction

from catalog.application.fachada import CatalogoQuery
from catalog.application.productos import UNIDADES_INICIALES
from catalog.application.puertos import puertos
from catalog.infrastructure.models import Unidad
from catalog.infrastructure.repositorios import CatalogoOrm
from tenancy.infrastructure.contenedor import tenancy_service


def caso_de_uso(clase):
    """`caso_de_uso(productos.CrearProducto).ejecutar(actor, …)`."""
    return clase(CatalogoOrm(), puertos, tenancy_service().limite_productos, transaction.atomic)


def catalogo_query() -> CatalogoQuery:
    return CatalogoQuery(CatalogoOrm())


def sembrar_unidades(empresa_id: int, admin_id: int, hoy: date) -> None:
    """Sembrador de 0001a: unidades iniciales con su código SUNAT (RF-CAT-01)."""
    Unidad.all_tenants.bulk_create(
        Unidad(empresa_id=empresa_id, nombre=n, abreviatura=a, codigo_sunat=c)
        for n, a, c in UNIDADES_INICIALES
    )
