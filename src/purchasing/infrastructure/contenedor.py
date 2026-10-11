"""Arma los casos de uso de compras con sus adaptadores reales."""

from django.db import transaction

from catalog.infrastructure.contenedor import catalogo_query
from purchasing.application.puertos import puertos
from purchasing.infrastructure.repositorios import ProveedoresOrm


def caso_de_uso(clase):
    """`caso_de_uso(proveedores.GuardarProveedor).ejecutar(actor, …)`."""
    return clase(ProveedoresOrm(), puertos, catalogo_query(), transaction.atomic)
