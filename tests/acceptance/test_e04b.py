"""Escenarios de la spec 0004b (criterio de aceptación ejecutable)."""

import pytest
from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_compras import *  # noqa: F403
from tests.acceptance.pasos_inventario import *  # noqa: F403
from tests.acceptance.pasos_proveedores import *  # noqa: F403

scenarios("0004b-Compras-anulacion/features")

# La concurrencia necesita transacciones reales: cada hilo usa su propia conexión (RF-COM-17).
test_doble_anulación_concurrente_revierte_una_sola_vez = pytest.mark.django_db(transaction=True)(  # noqa: F405
    test_doble_anulación_concurrente_revierte_una_sola_vez  # noqa: F405
)
