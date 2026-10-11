"""Arma el inventario con sus adaptadores reales."""

from datetime import date

from inventory.infrastructure.models import Almacen

PRINCIPAL = "Principal"


def sembrar_almacen(empresa_id: int, admin_id: int, hoy: date) -> None:
    """Sembrador de 0001a: almacén "Principal" (RF-INV-01)."""
    Almacen.all_tenants.create(empresa_id=empresa_id, nombre=PRINCIPAL)
