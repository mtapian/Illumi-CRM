"""Escenarios de la spec 0002e (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_impuestos import *  # noqa: F403

scenarios("0002e-Catalogo-impuestos/features")
