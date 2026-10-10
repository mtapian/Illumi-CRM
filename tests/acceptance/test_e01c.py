"""Escenarios de la spec 0001c (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_accesos import *  # noqa: F403
from tests.acceptance.pasos_sesion import *  # noqa: F403

scenarios("0001c-Tenancy-usuarios-roles/features")
