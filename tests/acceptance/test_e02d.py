"""Escenarios de la spec 0002d (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_proveedores import *  # noqa: F403

scenarios("0002d-Catalogo-proveedores/features")
