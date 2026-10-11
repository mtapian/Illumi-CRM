"""T2 y T3: habilitaciones de una empresa (RF-TEN-28, 30, 31, 33, 34; RN-TEN-08, 09)."""

from datetime import date, timedelta

import pytest

from shared.domain.accesos import CORE
from tenancy.domain.errores import CoreNoSeQuita
from tenancy.domain.habilitaciones import (
    Ajuste,
    ajuste_vigente,
    dependientes_afectados,
    estado_funcionalidad,
    funcionalidades_de_modulo,
    habilitaciones_efectivas,
)

HOY = date(2026, 10, 10)
EMPRENDEDOR = {
    "catalogo.productos",
    "inventario.stock",
    "inventario.ajustes",
    "compras.compras",
    "ventas.clientes",
    "ventas.ventas",
    "finanzas.gastos",
}


def test_un_ajuste_que_vence_hoy_sigue_vigente_y_uno_de_ayer_no():
    assert ajuste_vigente(Ajuste("inventario.multialmacen", "AGREGAR", HOY), HOY)
    assert not ajuste_vigente(Ajuste("inventario.multialmacen", "AGREGAR", HOY - timedelta(1)), HOY)
    assert ajuste_vigente(Ajuste("inventario.multialmacen", "AGREGAR", None), HOY)


def test_plan_mas_agregados_menos_quitados_y_core_siempre():
    ajustes = [
        Ajuste("inventario.multialmacen", "AGREGAR", None),
        Ajuste("inventario.ajustes", "QUITAR", None),
        Ajuste("produccion.recetas", "AGREGAR", HOY - timedelta(1)),  # vencido
    ]
    efectivas = habilitaciones_efectivas(EMPRENDEDOR, ajustes, HOY)
    assert "inventario.multialmacen" in efectivas
    assert "inventario.ajustes" not in efectivas
    assert "produccion.recetas" not in efectivas
    assert CORE <= efectivas
    assert CORE <= habilitaciones_efectivas(set(), [Ajuste(min(CORE), "QUITAR", None)], HOY)


def test_los_cuatro_estados():
    ajustes = [
        Ajuste("inventario.multialmacen", "AGREGAR", None),
        Ajuste("inventario.ajustes", "QUITAR", None),
    ]

    def estado(codigo):
        return estado_funcionalidad(codigo, EMPRENDEDOR, ajustes, HOY)

    assert estado("inventario.stock") == "Incluida en el plan"
    assert estado("inventario.ajustes") == "Quitada"
    assert estado("inventario.multialmacen") == "Agregada"
    assert estado("produccion.envasado") == "No incluida"


def test_quitar_stock_afecta_a_las_que_lo_requieren():
    afectadas = dependientes_afectados({"inventario.stock"}, EMPRENDEDOR)
    assert afectadas == ["inventario.ajustes", "compras.compras", "ventas.ventas"]


def test_quitar_un_modulo_completo_no_se_bloquea_a_si_mismo():
    produccion = set(funcionalidades_de_modulo("PRODUCCION"))
    assert produccion == {"produccion.recetas", "produccion.op", "produccion.envasado"}
    assert dependientes_afectados(produccion, EMPRENDEDOR | produccion) == []


def test_core_no_se_quita():
    with pytest.raises(CoreNoSeQuita):
        dependientes_afectados(set(funcionalidades_de_modulo("CORE")), EMPRENDEDOR)
