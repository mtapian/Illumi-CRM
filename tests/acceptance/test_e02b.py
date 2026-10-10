"""Escenarios de la spec 0002b (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403

scenarios("0002b-Catalogo-presentaciones/features")
