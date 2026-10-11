"""Pasos compartidos de los escenarios de aceptación (pytest-bdd)."""

import pytest

from tenancy.infrastructure.models import Empresa, Usuario


@pytest.fixture(autouse=True)
def _db(db):
    """Todos los escenarios usan la base de datos de test."""


@pytest.fixture
def ctx():
    """Estado compartido entre los pasos de un escenario."""
    return {"pendientes": []}


def contenido(respuesta) -> str:
    return respuesta.content.decode()


def no_hay_empresas_ni_usuarios_de_empresa() -> bool:
    return (
        not Empresa.objects.exists() and not Usuario.objects.filter(empresa__isnull=False).exists()
    )


def pytest_bdd_after_scenario(request, feature, scenario):
    """Un escenario con pasos que dependen de otras specs queda como skip parcial con motivo."""
    pendientes = request.getfixturevalue("ctx")["pendientes"]
    if pendientes:
        pytest.skip("Parcial; pendiente de otras specs: " + "; ".join(pendientes))


def pytest_bdd_apply_tag(tag, function):
    """`@borrador` (spec o enmienda sin aprobar) y `@pendiente-qN` (duda abierta del PRD) no se
    ejecutan: quedan como skip con su motivo (AGENTS.md §3)."""
    if tag == "borrador" or tag.startswith("pendiente-q"):
        motivo = "spec en borrador" if tag == "borrador" else f"duda abierta {tag[10:].upper()}"
        pytest.mark.skip(reason=f"{motivo}: no se ejecuta hasta su aprobación")(function)
        return True
    return None
