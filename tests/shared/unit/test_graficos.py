"""0008c, T1: gráficos SVG del inicio (RF-FIN-18 a 21, 24)."""

import re
from decimal import Decimal as D

import pytest

from shared.interfaces import graficos as g


@pytest.mark.parametrize(
    "maximo, tope",
    [(0, 1), (D("0.7"), 1), (1, 1), (130, 200), (288, 500), (4870, 5000), (D("1350"), 2000)],
)
def test_escala_redonda(maximo, tope):
    """El eje llega a 1, 2 o 5 × 10ⁿ, por encima del máximo (0 → 1)."""
    assert g.escala(maximo) == tope


def valores(svg):
    return [D(v) for v in re.findall(r'data-valor="([^"]+)"', svg)]


def test_linea_un_punto_por_etiqueta_con_su_valor():
    svg = g.linea([("30/11", D("0")), ("01/12", D("288.00")), ("02/12", D("60"))])
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert valores(svg) == [D("0"), D("288.00"), D("60.00")]
    assert "01/12" in svg and "S/ 288.00" in svg  # etiqueta del eje y valor visible
    assert "S/ 500" in svg  # tope del eje


def test_dona_con_monto_y_porcentaje():
    svg = g.dona([("Efectivo", D("200")), ("Yape", D("88")), ("Plin", D("0"))])
    assert valores(svg) == [D("200.00"), D("88.00")]  # sin segmentos en 0
    assert "Efectivo" in svg and "S/ 200.00 (69 %)" in svg and "S/ 88.00 (31 %)" in svg


def test_barras_de_mayor_a_menor():
    svg = g.barras([("Snacks", D("40")), ("Cervezas", D("348"))])
    assert re.findall(r'data-etiqueta="([^"]+)"', svg) == ["Cervezas", "Snacks"]
    assert "S/ 348.00" in svg


@pytest.mark.parametrize("dibujar", [g.dona, g.barras])
def test_sin_datos_no_falla(dibujar):
    """RF-FIN-24."""
    assert "Aún no hay ventas" in dibujar([]) and "Aún no hay ventas" in dibujar([("A", 0)])


def test_linea_sin_datos_dibuja_los_ejes_en_cero():
    svg = g.linea([("01/12", D("0")), ("02/12", D("0"))])
    assert valores(svg) == [D("0"), D("0")] and "S/ 1" in svg


def test_escapa_las_etiquetas():
    assert "A &amp; B" in g.barras([("A & B", D("1"))])
