"""Escenarios de la spec 0003b (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_inventario import *  # noqa: F403

scenarios("0003b-Inventario-ajustes/features")
