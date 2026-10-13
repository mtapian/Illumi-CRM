"""Exportación de grillas a XLSX y CSV (spec 0008c, RF-FIN-15, 25).

Sin dependencias (PO, Q6): el XLSX es un ZIP con XML (cadenas en línea, sin estilos); se
escribe fila a fila sobre un archivo temporal y el CSV se envía por streaming, así una
exportación grande no se carga entera en memoria (RNF-FIN-05).
"""

import csv
import io
import tempfile
import zipfile
from datetime import date, datetime
from decimal import Decimal
from xml.sax.saxutils import escape

from django.contrib import messages
from django.http import FileResponse, StreamingHttpResponse
from django.shortcuts import redirect
from django.utils import timezone

from shared.domain.errores import DomainError

TOPE = 50_000
FORMATOS = ("xlsx", "csv")
BOM = "﻿"

_PARTES = {
    "[Content_Types].xml": (
        '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/'
        'package/2006/content-types"><Default Extension="rels" ContentType="application/'
        'vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType='
        '"application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName='
        '"/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.spreadsheetml.worksheet+xml"/></Types>'
    ),
    "_rels/.rels": (
        '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
        'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
        'schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    ),
    "xl/workbook.xml": (
        '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.'
        'org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships"><sheets><sheet name="Datos" sheetId="1" '
        'r:id="rId1"/></sheets></workbook>'
    ),
    "xl/_rels/workbook.xml.rels": (
        '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
        'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
        'schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    ),
}


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return timezone.localtime(valor).strftime("%Y-%m-%d %H:%M")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return format(valor, "f")
    return str(valor)


def _columna(i: int) -> str:
    letras = ""
    i += 1
    while i:
        i, resto = divmod(i - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _fila(n: int, valores) -> str:
    celdas = []
    for i, valor in enumerate(valores):
        ref = f"{_columna(i)}{n}"
        if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool):
            celdas.append(f'<c r="{ref}" t="n"><v>{_texto(valor)}</v></c>')
        elif valor not in (None, ""):
            limpio = "".join(c for c in _texto(valor) if c >= " " or c in "\t\n")
            celdas.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(limpio)}</t></is></c>')
    return f'<row r="{n}">{"".join(celdas)}</row>'


def _xlsx(columnas, filas):
    archivo = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
    with zipfile.ZipFile(archivo, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, xml in _PARTES.items():
            z.writestr(nombre, xml)
        with z.open("xl/worksheets/sheet1.xml", "w") as hoja:
            hoja.write(
                b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.'
                b'openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            )
            hoja.write(_fila(1, columnas).encode())
            for n, valores in enumerate(filas, 2):
                hoja.write(_fila(n, valores).encode())
            hoja.write(b"</sheetData></worksheet>")
    archivo.seek(0)
    return archivo


def _csv(columnas, filas):
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    yield BOM
    escritor.writerow(columnas)
    yield buffer.getvalue()
    for valores in filas:
        buffer.seek(0)
        buffer.truncate()
        escritor.writerow([_texto(v) for v in valores])
        yield buffer.getvalue()


def respuesta(nombre: str, columnas, filas, formato: str, total: int):
    """La descarga `nombre.formato`; `filas` es un iterable (p. ej. `qs.iterator()`) y `total`
    su cantidad, que se valida contra el tope antes de generar nada."""
    if formato not in FORMATOS:
        raise DomainError("Formato de exportación no válido")
    if total > TOPE:
        raise DomainError("Hay más de 50 000 filas: agrega filtros para exportar")
    if formato == "csv":
        r = StreamingHttpResponse(_csv(columnas, filas), content_type="text/csv")
        r["Content-Disposition"] = f'attachment; filename="{nombre}.csv"'
        return r
    tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        _xlsx(columnas, filas), as_attachment=True, filename=f"{nombre}.xlsx", content_type=tipo
    )


PERMISO = "reportes.exportar"


def desde_grilla(request, nombre: str, columnas, filas, preparar=None):
    """Si la grilla pide `?formato=xlsx|csv`, la descarga con sus filtros; si no, None.
    `columnas`: [(título, función(fila) -> valor)]; `filas`: queryset o lista. Exige
    `reportes.exportar` (RF-FIN-15); con más filas que el tope vuelve a la grilla con el aviso
    (RF-FIN-25)."""
    formato = request.GET.get("formato")
    if not formato:
        return None
    request.actor.exige(PERMISO)
    total = filas.count() if hasattr(filas, "count") and not isinstance(filas, list) else len(filas)
    recorrer = filas.iterator(chunk_size=2000) if hasattr(filas, "iterator") else iter(filas)
    if preparar:  # una vez por fila, antes de sus columnas
        recorrer = map(preparar, recorrer)
    try:
        return respuesta(
            nombre,
            [titulo for titulo, _ in columnas],
            ([funcion(x) for _, funcion in columnas] for x in recorrer),
            formato,
            total,
        )
    except DomainError as e:
        messages.error(request, e.mensaje)
        sin = request.GET.copy()
        sin.pop("formato", None)
        return redirect(f"{request.path}?{sin.urlencode()}" if sin else request.path)
