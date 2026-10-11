"""Arma los casos de uso de compras con sus adaptadores reales."""

from django.db import transaction

from catalog.infrastructure.contenedor import catalogo_query
from inventory.infrastructure.contenedor import inventario
from purchasing.application.puertos import puertos
from purchasing.infrastructure.repositorios import ComprasOrm, ProveedoresOrm
from shared.infrastructure.secuencia import SecuenciaPostgres
from tenancy.infrastructure.contenedor import tenancy_service


def caso_de_uso(clase):
    """`caso_de_uso(proveedores.GuardarProveedor).ejecutar(actor, …)`."""
    return clase(ProveedoresOrm(), puertos, catalogo_query(), transaction.atomic)


def caso_de_compra(clase):
    """`caso_de_compra(compras.CrearCompra).ejecutar(actor, …)`."""
    return clase(
        ComprasOrm(),
        catalogo_query(),
        tenancy_service(),
        SecuenciaPostgres(),
        inventario(),
        transaction.atomic,
    )
