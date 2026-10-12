"""Arma los casos de uso del catálogo con sus adaptadores reales."""

from datetime import date

from django.db import transaction

from catalog.application import impuestos
from catalog.application.fachada import CatalogoQuery
from catalog.application.productos import UNIDADES_INICIALES
from catalog.application.puertos import puertos
from catalog.infrastructure.models import Impuesto, ImpuestoTasa, Unidad
from catalog.infrastructure.repositorios import CatalogoOrm, ImpuestosOrm
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import tenancy_service


def caso_de_uso(clase):
    """`caso_de_uso(productos.CrearProducto).ejecutar(actor, …)`."""
    return clase(CatalogoOrm(), puertos, tenancy_service().limite_productos, transaction.atomic)


def caso_de_impuestos(clase):
    return clase(ImpuestosOrm(), transaction.atomic)


def catalogo_query() -> CatalogoQuery:
    return CatalogoQuery(CatalogoOrm())


def sembrar_unidades(empresa_id: int, admin_id: int, hoy: date) -> None:
    """Sembrador de 0001a: unidades iniciales con su código SUNAT (RF-CAT-01)."""
    Unidad.all_tenants.bulk_create(
        Unidad(empresa_id=empresa_id, nombre=n, abreviatura=a, codigo_sunat=c)
        for n, a, c in UNIDADES_INICIALES
    )


def sembrar_impuestos(empresa_id: int, admin_id: int, hoy: date) -> None:
    """Sembrador de 0001a: IGV, Exonerado e Inafecto de venta y de compra (RF-CAT-52)."""
    with tenant_context(empresa_id):
        igv = tenancy_service().igv_vigente(hoy)
    for tipo in impuestos.TIPOS:
        for nombre, codigo in impuestos.INICIALES:
            impuesto = Impuesto.all_tenants.create(
                empresa_id=empresa_id, nombre=nombre, tipo=tipo, codigo=codigo
            )
            ImpuestoTasa.all_tenants.create(
                empresa_id=empresa_id,
                impuesto=impuesto,
                vigente_desde=hoy,
                importe=igv if codigo == impuestos.IGV else 0,
                creado_por_id=admin_id,
            )
