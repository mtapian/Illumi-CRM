"""T1 y T2 de 0002b: presentación y materiales (RF-CAT-15, 16; RN-CAT-04, 05; RNF-CAT-02)."""

from decimal import Decimal

import pytest

from catalog.domain.errores import PresentacionInvalida
from catalog.domain.presentacion import materiales_para, validar_presentacion
from catalog.domain.tipos import TipoProducto as T

ENVASES = [(T.ENVASE, Decimal("1")), (T.ENVASE, Decimal("0.0417"))]


def validar(**kw):
    base = dict(granel=(T.GRANEL, True), contenido=Decimal("0.33"), materiales=ENVASES)
    validar_presentacion(**(base | kw))


def test_acepta_fracciones_de_material():
    validar()


@pytest.mark.parametrize(
    "cambio, mensaje",
    [
        ({"contenido": Decimal("0")}, "El contenido debe ser mayor a 0 litros"),
        ({"granel": (T.GRANEL, False)}, "El granel de origen está inactivo"),
        ({"granel": (T.INSUMO, True)}, "El origen debe ser un producto tipo GRANEL"),
        ({"materiales": []}, "La presentación requiere al menos un material de envase"),
        (
            {"materiales": [(T.INSUMO, Decimal("1"))]},
            "Los materiales deben ser productos tipo ENVASE",
        ),
        (
            {"materiales": [(T.ENVASE, Decimal("0"))]},
            "La cantidad de cada material debe ser mayor a 0",
        ),
    ],
)
def test_rechazos(cambio, mensaje):
    with pytest.raises(PresentacionInvalida, match=mensaje):
        validar(**cambio)


def test_materiales_para_240_unidades_con_4_decimales():
    pedido = materiales_para({1: Decimal("1"), 2: Decimal("0.0417")}, Decimal("240"))
    assert pedido == {1: Decimal("240.0000"), 2: Decimal("10.0080")}
