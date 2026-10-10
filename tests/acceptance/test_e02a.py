"""Escenarios de la spec 0002a (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403

scenarios("0002a-Catalogo-productos/features")
