"""Escenarios de la spec 0001b (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_plataforma import *  # noqa: F403

scenarios("0001b-Tenancy-plataforma-habilitaciones/features")
