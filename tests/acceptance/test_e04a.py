"""Escenarios de la spec 0004a (criterio de aceptación ejecutable)."""

from pytest_bdd import scenarios

from tests.acceptance.pasos_catalogo import *  # noqa: F403
from tests.acceptance.pasos_compras import *  # noqa: F403
from tests.acceptance.pasos_inventario import *  # noqa: F403
from tests.acceptance.pasos_proveedores import *  # noqa: F403

scenarios("0004a-Compras-proveedores-registro/features")
