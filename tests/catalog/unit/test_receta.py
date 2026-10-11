"""0002a enmienda 4, T35: receta opcional de uno o varios componentes (RF-CAT-41)."""

from decimal import Decimal as D

import pytest

from catalog.domain.errores import RecetaInvalida
from catalog.domain.receta import componentes_para, hay_ciclo, validar_receta
from catalog.domain.tipos import TipoProducto as T

ACTIVOS = {2: (T.BIEN, True), 3: (T.BIEN, True), 4: (T.SERVICIO, True), 5: (T.BIEN, False)}


def test_uno_o_varios_componentes_incluso_servicios():
    validar_receta(1, [(2, D("0.2"))], ACTIVOS)
    validar_receta(1, [(2, D("0.33")), (3, D("1")), (4, D("0.5"))], ACTIVOS)
    validar_receta(1, [], ACTIVOS)  # sin receta: es opcional


@pytest.mark.parametrize(
    "componentes, mensaje",
    [
        ([(1, D("1"))], "Un producto no puede ser componente de sí mismo"),
        ([(2, D("1")), (2, D("2"))], "Un componente está repetido en la receta"),
        ([(2, D("0"))], "La cantidad de cada componente debe ser mayor a 0"),
        ([(5, D("1"))], "Un componente no existe o está inactivo"),
        ([(9, D("1"))], "Un componente no existe o está inactivo"),
    ],
)
def test_rechazos(componentes, mensaje):
    with pytest.raises(RecetaInvalida, match=mensaje):
        validar_receta(1, componentes, ACTIVOS)


def test_ciclos():
    grafo = {10: {11}, 11: {12}}  # 10 usa 11, 11 usa 12
    assert hay_ciclo(grafo, 12, {10})  # 12 → 10 → 11 → 12
    assert not hay_ciclo(grafo, 13, {10})
    assert not hay_ciclo(grafo, 10, {12})  # reemplaza su receta: 10 → 12, sin vuelta


def test_componentes_para_una_cantidad():
    receta = ((2, D("0.33")), (3, D("0.0417")))
    assert componentes_para(receta, D("1000")) == {2: D("330.0000"), 3: D("41.7000")}
    assert componentes_para(receta, D("3")) == {2: D("0.9900"), 3: D("0.1251")}
