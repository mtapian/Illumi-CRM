"""Escenarios de la spec 0003a (criterio de aceptación ejecutable)."""

import pytest
from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_inventario import *  # noqa: F403

scenarios("0003a-Inventario-movimientos-costo/features")

# La concurrencia necesita transacciones reales: cada hilo usa su propia conexión (RF-INV-19).
test_concurrencia_sobre_el_último_stock = pytest.mark.django_db(transaction=True)(  # noqa: F405
    test_concurrencia_sobre_el_último_stock  # noqa: F405
)
