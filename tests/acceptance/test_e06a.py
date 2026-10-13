"""Escenarios de la spec 0006a (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_inventario import *  # noqa: F403
from tests.acceptance.pasos_produccion import *  # noqa: F403
from tests.acceptance.pasos_ventas import *  # noqa: F403

scenarios("0006a-Ventas-clientes-pedidos/features")
