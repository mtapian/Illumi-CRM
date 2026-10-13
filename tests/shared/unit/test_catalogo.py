"""T1: catálogo de módulos, funcionalidades y permisos (RF-TEN-26, 31; RN-TEN-09)."""

from shared.domain.accesos import (
    CATALOGO,
    MODULOS,
    PERMISOS,
    dependencias_faltantes,
    funcionalidad,
    requeridas,
)


def test_cada_funcionalidad_tiene_modulo_conocido_y_dependencias_existentes():
    for f in CATALOGO.values():
        assert f.modulo in MODULOS
        assert set(f.requiere) <= set(CATALOGO)


def test_el_catalogo_no_tiene_ciclos():
    for codigo in CATALOGO:
        assert codigo not in requeridas(codigo)


def test_cada_permiso_pertenece_a_una_sola_funcionalidad():
    todos = [p for f in CATALOGO.values() for p in f.permisos]
    assert len(todos) == len(set(todos)) == len(PERMISOS)
    assert PERMISOS["ventas.venta.anular"] == "ventas.ventas"


def test_ajustes_sin_sus_dependencias_indica_las_que_faltan_en_orden():
    faltan = dependencias_faltantes({"inventario.ajustes"})
    assert [funcionalidad(c).nombre for c in faltan] == [
        "Productos y presentaciones",
        "Stock y kardex",
    ]
