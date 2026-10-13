"""0008c, T2: exportación a XLSX y CSV (RF-FIN-15, 25)."""

import io
import re
import zipfile
from datetime import date
from decimal import Decimal as D

import pytest

from shared.domain.errores import DomainError
from shared.interfaces import exportar

COLUMNAS = ["Pedido", "Fecha", "SKU", "Cantidad", "Total"]
FILAS = [
    ["P-000001", date(2026, 12, 1), "TER-IPA-330", D("24"), D("288.00")],
    ["P-000002", date(2026, 12, 2), "A & B <x>", D("1.5"), D("12.00")],
]


def contenido(respuesta) -> bytes:
    return b"".join(respuesta.streaming_content) if respuesta.streaming else respuesta.content


def test_csv_con_bom_y_punto_decimal():
    r = exportar.respuesta("pedidos", COLUMNAS, iter(FILAS), "csv", total=2)
    datos = contenido(r)
    assert datos.startswith("﻿".encode())
    assert r["Content-Disposition"] == 'attachment; filename="pedidos.csv"'
    lineas = datos.decode("utf-8-sig").splitlines()
    assert lineas[0] == "Pedido,Fecha,SKU,Cantidad,Total"
    assert lineas[1] == "P-000001,2026-12-01,TER-IPA-330,24,288.00"


def hoja(datos: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        assert {"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml"} <= set(
            z.namelist()
        )
        return z.read("xl/worksheets/sheet1.xml").decode()


def test_xlsx_se_vuelve_a_leer():
    r = exportar.respuesta("pedidos", COLUMNAS, iter(FILAS), "xlsx", total=2)
    assert r["Content-Disposition"] == 'attachment; filename="pedidos.xlsx"'
    xml = hoja(contenido(r))
    assert len(re.findall(r"<row ", xml)) == 3  # encabezado + 2
    assert "<t>Pedido</t>" in xml and "<t>A &amp; B &lt;x&gt;</t>" in xml
    assert '<c r="E2" t="n"><v>288.00</v></c>' in xml  # números como números
    assert "<t>2026-12-01</t>" in xml


def test_tope_de_filas():
    """RF-FIN-25."""
    with pytest.raises(DomainError, match="Hay más de 50 000 filas: agrega filtros para exportar"):
        exportar.respuesta("x", COLUMNAS, iter([]), "xlsx", total=50_001)


def test_formato_desconocido():
    with pytest.raises(DomainError, match="Formato de exportación no válido"):
        exportar.respuesta("x", COLUMNAS, iter([]), "pdf", total=0)
