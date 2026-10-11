"""Arma el inventario con sus adaptadores reales."""

from datetime import date

from catalog.infrastructure.contenedor import catalogo_query
from inventory.application.servicio import InventarioService
from inventory.infrastructure.models import Almacen
from inventory.infrastructure.repositorios import InventarioOrm

PRINCIPAL = "Principal"


def inventario() -> InventarioService:
    """`inventario().registrar_entrada(…)`, dentro de la transacción del caso de uso."""
    return InventarioService(InventarioOrm(), catalogo_query())


def sembrar_almacen(empresa_id: int, admin_id: int, hoy: date) -> None:
    """Sembrador de 0001a: almacén "Principal" (RF-INV-01)."""
    Almacen.all_tenants.create(empresa_id=empresa_id, nombre=PRINCIPAL)
