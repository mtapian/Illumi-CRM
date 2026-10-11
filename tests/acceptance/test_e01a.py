"""Escenarios de la spec 0001a (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_registro import *  # noqa: F403
from tests.acceptance.pasos_sesion import *  # noqa: F403
from tests.acceptance.pasos_suscripcion import *  # noqa: F403

scenarios("0001a-Tenancy-registro-sesion/features")
