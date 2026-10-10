"""T7: todo caso de uso declara un permiso del catálogo y se rechaza sin él
(RF-TEN-49, RNF-TEN-06). Cubre los casos de uso de todas las épicas."""

import importlib
import pkgutil
from pathlib import Path

import pytest

from shared.application.autorizacion import Actor, CasoDeUso
from shared.domain.accesos import PERMISOS
from shared.domain.errores import AccesoDenegado

SRC = Path(__file__).resolve().parents[2] / "src"


def _casos_de_uso():
    for contexto in SRC.iterdir():
        aplicacion = contexto / "application"
        if aplicacion.is_dir():
            for modulo in pkgutil.iter_modules([str(aplicacion)]):
                importlib.import_module(f"{contexto.name}.application.{modulo.name}")

    def subclases(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from subclases(sub)

    con_accion = (c for c in subclases(CasoDeUso) if hasattr(c, "ejecutar"))
    return sorted(con_accion, key=lambda c: c.__qualname__)


CASOS = _casos_de_uso()


def test_hay_casos_de_uso_protegidos():
    assert CASOS


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.__qualname__)
def test_declara_un_permiso_del_catalogo_y_se_rechaza_sin_el(caso):
    assert caso.permiso_requerido in PERMISOS
    instancia = object.__new__(caso)
    with pytest.raises(AccesoDenegado):
        instancia.ejecutar(Actor(usuario_id=1, empresa_id=1, permisos=frozenset()))
