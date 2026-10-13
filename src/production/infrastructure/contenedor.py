"""Arma los casos de uso de producción con sus adaptadores reales."""

from django.db import transaction

from catalog.infrastructure.contenedor import catalogo_query
from inventory.infrastructure.contenedor import inventario
from production.infrastructure.repositorios import OrdenesOrm
from shared.infrastructure.secuencia import SecuenciaPostgres


def caso_de_op(clase):
    """`caso_de_op(ordenes.CrearOp).ejecutar(actor, …)`."""
    return clase(
        OrdenesOrm(), catalogo_query(), inventario(), SecuenciaPostgres(), transaction.atomic
    )
