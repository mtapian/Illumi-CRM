"""Gráficos del inicio como SVG generado en el servidor (spec 0008c, RF-FIN-18 a 21, 24).

Sin JavaScript ni dependencias (PO, Q5): los valores se ven en etiquetas. Los importes llegan
como `Decimal`; solo las coordenadas usan `float`.
"""

from decimal import ROUND_HALF_UP, Decimal
from html import escape
from math import cos, pi, sin

CENTIMO = Decimal("0.01")
COLORES = ("#5ab4d6", "#e9a24f", "#b0359e", "#c3cb46", "#3f7ad6", "#6cc3a0", "#e46a6a")
SIN_DATOS = '<p class="subtitulo">Aún no hay ventas.</p>'


def escala(maximo) -> Decimal:
    """Tope del eje: 1, 2 o 5 × 10ⁿ, el primero que alcanza al máximo (0 → 1)."""
    maximo = Decimal(maximo)
    if maximo <= 0:
        return Decimal(1)
    base = Decimal(10) ** maximo.adjusted()
    return next(f * base for f in (1, 2, 5, 10) if f * base >= maximo)


def soles(valor) -> str:
    return f"S/ {Decimal(valor).quantize(CENTIMO, ROUND_HALF_UP):,f}"


def _eje(valor: Decimal) -> str:
    v = valor.normalize()
    return f"S/ {v.quantize(Decimal(1)) if v == v.to_integral() else v:,f}"


def _svg(ancho, alto, cuerpo, titulo) -> str:
    return (
        f'<svg class="grafico" viewBox="0 0 {ancho} {alto}" role="img" '
        f'aria-label="{escape(titulo)}" xmlns="http://www.w3.org/2000/svg">{cuerpo}</svg>'
    )


def linea(puntos, titulo="Ventas", ancho=600, alto=240) -> str:
    """Un punto por etiqueta, unidos; eje en S/ con 5 divisiones; el valor sobre cada punto
    mayor a 0. Sin ventas, los ejes en 0 (RF-FIN-24)."""
    izq, der, arriba, abajo = 64, 16, 16, 28
    alto_util, ancho_util = alto - arriba - abajo, ancho - izq - der
    tope = escala(max((Decimal(v) for _, v in puntos), default=0))
    partes = []
    for i in range(6):  # líneas guía y etiquetas del eje
        y = arriba + alto_util * i / 5
        valor = tope * (5 - i) / 5
        partes.append(
            f'<line x1="{izq}" y1="{y:.1f}" x2="{ancho - der}" y2="{y:.1f}" class="guia"/>'
            f'<text x="{izq - 6}" y="{y + 4:.1f}" text-anchor="end">{_eje(valor)}</text>'
        )
    paso = ancho_util / max(len(puntos) - 1, 1)
    coords = []
    for i, (etiqueta, valor) in enumerate(puntos):
        valor = Decimal(valor).quantize(CENTIMO, ROUND_HALF_UP)
        x = izq + paso * i
        y = arriba + alto_util * float(1 - valor / tope)
        coords.append(f"{x:.1f},{y:.1f}")
        partes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" data-etiqueta="{escape(str(etiqueta))}"'
            f' data-valor="{valor}"><title>{escape(str(etiqueta))}: {soles(valor)}</title>'
            f'</circle><text x="{x:.1f}" y="{alto - 8}" text-anchor="middle">'
            f"{escape(str(etiqueta))}</text>"
        )
        if valor > 0:
            partes.append(
                f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" class="valor">'
                f"{soles(valor)}</text>"
            )
    trazo = f'<polyline points="{" ".join(coords)}" class="trazo"/>'
    return _svg(ancho, alto, trazo + "".join(partes), titulo)


def dona(segmentos, titulo="Cobrado por método de pago", lado=200) -> str:
    """Una porción por segmento mayor a 0, con leyenda de monto y porcentaje (RF-FIN-20)."""
    segmentos = [(e, Decimal(v)) for e, v in segmentos if Decimal(v) > 0]
    total = sum((v for _, v in segmentos), Decimal(0))
    if not total:
        return SIN_DATOS
    centro, radio, partes, inicio = lado / 2, lado / 2 - 20, [], 0.0
    leyenda = []
    for i, (etiqueta, valor) in enumerate(segmentos):
        color = COLORES[i % len(COLORES)]
        fraccion = float(valor / total)
        fin = inicio + fraccion * 2 * pi
        x1, y1 = centro + radio * sin(inicio), centro - radio * cos(inicio)
        x2, y2 = centro + radio * sin(fin), centro - radio * cos(fin)
        grande = 1 if fin - inicio > pi else 0
        if len(segmentos) == 1:  # un círculo completo
            forma = f'<circle cx="{centro}" cy="{centro}" r="{radio}"'
        else:
            forma = (
                f'<path d="M {x1:.2f} {y1:.2f} A {radio} {radio} 0 {grande} 1 {x2:.2f} {y2:.2f}"'
            )
        porcentaje = (valor * 100 / total).quantize(Decimal(1), ROUND_HALF_UP)
        texto = f"{escape(etiqueta)} {soles(valor)} ({porcentaje} %)"
        partes.append(
            f'{forma} fill="none" stroke="{color}" stroke-width="34" data-etiqueta='
            f'"{escape(etiqueta)}" data-valor="{valor.quantize(CENTIMO)}"><title>{texto}</title>'
            + ("</circle>" if len(segmentos) == 1 else "</path>")
        )
        y = 24 + i * 22
        leyenda.append(
            f'<rect x="{lado + 10}" y="{y - 10}" width="12" height="12" fill="{color}"/>'
            f'<text x="{lado + 28}" y="{y}">{texto}</text>'
        )
        inicio = fin
    return _svg(lado + 260, max(lado, 24 + len(segmentos) * 22), "".join(partes + leyenda), titulo)


def barras(items, titulo="Ventas por categoría", ancho=600) -> str:
    """Barras horizontales de mayor a menor con su valor (RF-FIN-21)."""
    items = sorted(((e, Decimal(v)) for e, v in items if Decimal(v) > 0), key=lambda x: -x[1])
    if not items:
        return SIN_DATOS
    izq, der, fila = 120, 90, 34
    tope, partes = escala(items[0][1]), []
    for i, (etiqueta, valor) in enumerate(items):
        y = 8 + i * fila
        largo = (ancho - izq - der) * float(valor / tope)
        partes.append(
            f'<text x="{izq - 8}" y="{y + 18}" text-anchor="end">{escape(etiqueta)}</text>'
            f'<rect x="{izq}" y="{y}" width="{largo:.1f}" height="24" rx="3" class="barra" '
            f'data-etiqueta="{escape(etiqueta)}" data-valor="{valor.quantize(CENTIMO)}"/>'
            f'<text x="{izq + largo + 6:.1f}" y="{y + 18}">{soles(valor)}</text>'
        )
    return _svg(ancho, 16 + len(items) * fila, "".join(partes), titulo)
