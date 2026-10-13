"""Escenarios de la spec 0006b (criterio de aceptación ejecutable)."""

import pytest
from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_facturacion import *  # noqa: F403
from tests.acceptance.pasos_inventario import *  # noqa: F403
from tests.acceptance.pasos_produccion import *  # noqa: F403
from tests.acceptance.pasos_ventas import *  # noqa: F403

scenarios("0006b-Ventas-registro-venta/features")

# La concurrencia necesita transacciones reales: cada hilo usa su propia conexión (RF-VEN-26).
test_dos_usuarios_facturan_a_la_vez_el_último_stock = pytest.mark.django_db(transaction=True)(  # noqa: F405
    test_dos_usuarios_facturan_a_la_vez_el_último_stock  # noqa: F405
)
