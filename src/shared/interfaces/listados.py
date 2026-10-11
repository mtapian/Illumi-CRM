"""Grillas estándar (docs/ux.md §3): paginación, consulta sin la página y filtros aplicados."""

from urllib.parse import urlencode

from django.core.paginator import Page, Paginator

POR_PAGINA = 25


def paginar(request, filas, por_pagina: int = POR_PAGINA) -> Page:
    return Paginator(filas, por_pagina).get_page(request.GET.get("pagina"))


def consulta(request, sin: tuple[str, ...] = ("pagina",)) -> str:
    """Los filtros de la URL sin `sin` (para paginar o exportar sin perderlos)."""
    return urlencode([(k, v) for k, v in request.GET.items() if k not in sin and v.strip()])


def aplicados(request, campos: dict, defectos: dict | None = None) -> list[dict]:
    """Filtros con valor (distinto del de por defecto), para mostrarlos como chips y quitarlos
    uno a uno. `campos`: {parámetro: (etiqueta, {valor: texto} o None)}; una casilla marcada
    ("1") muestra solo su etiqueta."""
    defectos = defectos or {}
    chips = []
    for clave, (etiqueta, nombres) in campos.items():
        valor = request.GET.get(clave, "").strip()
        if not valor or valor == defectos.get(clave):
            continue
        texto = "" if valor == "1" and nombres is None else (nombres or {}).get(valor, valor)
        quitar = "?" + consulta(request, (clave, "pagina"))
        chips.append({"etiqueta": etiqueta, "valor": texto, "quitar": quitar})
    return chips
