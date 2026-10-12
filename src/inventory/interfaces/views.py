"""Pantallas del inventario (plan 0003a §5)."""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from catalog.infrastructure.models import Categoria, Producto
from inventory.application import ajustes as ua
from inventory.application import almacenes as uc
from inventory.application.ajustes import LineaAjuste
from inventory.domain.ajuste import TIPOS
from inventory.domain.errores import AjusteInvalido
from inventory.infrastructure import consultas
from inventory.infrastructure.contenedor import caso_de_ajuste, caso_de_uso
from inventory.infrastructure.models import Ajuste, Almacen, Movimiento
from shared.interfaces import listados
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

MIGAS = [("Inicio", "/"), ("Inventario", None)]


@requiere(uc.GESTIONAR)
def almacenes(request):
    """Listado de maestro (ADR-12; RF-INV-02, 03): `?nuevo=1` y `?editar=<id>` abren el
    formulario en su propia página (RF-CAT-51)."""
    if request.method == "POST":
        p, actor = request.POST, request.actor
        id_ = int(p["id"]) if p.get("id", "").isdigit() else None
        acciones = {
            "guardar": lambda: caso_de_uso(uc.GuardarAlmacen).ejecutar(
                actor, id_, p.get("nombre", "")
            ),
            "activar": lambda: caso_de_uso(uc.CambiarEstadoAlmacen).ejecutar(actor, id_, True),
            "desactivar": lambda: caso_de_uso(uc.CambiarEstadoAlmacen).ejecutar(actor, id_, False),
        }
        if _intentar(request, acciones.get(p.get("accion"), acciones["guardar"])):
            messages.success(request, "Cambio guardado.")
            return redirect(request.path)
    todas = Almacen.objects.annotate(
        n_productos=Count("stock__producto", filter=Q(stock__cantidad__gt=0), distinct=True)
    ).order_by("nombre")
    q = request.GET.get("q", "").strip()
    editar = request.GET.get("editar", "")
    # Si un "guardar" falló, el formulario vuelve con lo enviado y el error en su campo.
    fallo = request.method == "POST" and request.POST.get("accion", "guardar") == "guardar"
    if fallo and request.POST.get("id", "").isdigit():
        editar = request.POST["id"]
    editando = get_object_or_404(todas, pk=editar) if editar.isdigit() else None  # art. 3.1
    nuevo = "nuevo" in request.GET or (fallo and not editando)
    migas = MIGAS + [("Almacenes", None)]
    if nuevo or editando:
        migas = MIGAS + [("Almacenes", request.path), ("Editar" if editando else "Nuevo", None)]
    nombre = request.POST.get("nombre") if request.method == "POST" else None
    contexto = {
        "filas": todas.filter(nombre__icontains=q) if q else todas,
        "q": q,
        "nuevo": nuevo,
        "editando": editando,
        "nombre": nombre if nombre is not None else (editando.nombre if editando else ""),
        "migas": migas,
    }
    return render(request, "inventory/almacenes.html", contexto)


CAMPOS_LINEA = ("producto", "cantidad", "lote", "vencimiento", "costo", "sentido")


def _numero(texto, campo):
    if not texto:
        return None
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise AjusteInvalido(f"{campo} no es un número válido") from None


def _filas(post) -> list[dict]:
    """Las líneas enviadas: una por producto, sin límite (plan 0003b §6). Cada línea manda
    todos sus campos, así que las listas quedan alineadas."""
    columnas = [post.getlist(c) for c in CAMPOS_LINEA]
    return [
        dict(zip(CAMPOS_LINEA, valores, strict=False)) for valores in zip(*columnas, strict=False)
    ]


def _lineas(post) -> list[LineaAjuste]:
    lineas = []
    for f in _filas(post):
        if not f["producto"].isdigit():
            continue
        lineas.append(
            LineaAjuste(
                int(f["producto"]),
                _numero(f["cantidad"], "La cantidad") or Decimal("0"),
                _numero(f["costo"], "El costo unitario"),
                f["lote"].strip() or None,
                date.fromisoformat(f["vencimiento"]) if f["vencimiento"] else None,
                f["sentido"],
            )
        )
    return lineas


@requiere(ua.REGISTRAR)
def ajustes(request):
    """ "Nuevo ajuste" y "Últimos ajustes" en dos tarjetas (plan 0003b §5; RF-INV-08 a 12)."""
    if request.method == "POST":
        p, nuevo = request.POST, {}

        def registrar():
            destino = int(p["destino"]) if p.get("destino", "").isdigit() else None
            caso = caso_de_ajuste(ua.RegistrarAjuste)
            almacen = int(p["almacen"]) if p.get("almacen", "").isdigit() else 0
            tipo, motivo, hoy = p.get("tipo", ""), p.get("motivo", ""), timezone.localdate()
            lineas = _lineas(p)
            nuevo["id"] = caso.ejecutar(request.actor, tipo, almacen, motivo, lineas, destino, hoy)

        if _intentar(request, registrar):
            messages.success(request, "Ajuste registrado.")
            return redirect("ajuste", ajuste_id=nuevo["id"])
    contexto = {
        "tipos": TIPOS,
        "almacenes": Almacen.objects.filter(activo=True).order_by("nombre"),
        "productos": Producto.objects.filter(activo=True, tipo="BIEN")
        .select_related("unidad")
        .order_by("nombre"),
        # Si el ajuste se rechaza, vuelven las líneas ingresadas; si no, una vacía.
        "filas": (_filas(request.POST) if request.method == "POST" else []) or [{}],
        "valores": request.POST if request.method == "POST" else {},
        "ultimos": Ajuste.objects.select_related("almacen").order_by("-numero")[:15],
        "migas": MIGAS + [("Ajustes", None)],
    }
    return render(request, "inventory/ajustes.html", contexto)


@requiere(ua.REGISTRAR)
def ajuste(request, ajuste_id):
    """Detalle del ajuste y "Anular" con motivo (RF-INV-13)."""
    fila = get_object_or_404(
        Ajuste.objects.select_related("almacen", "almacen_destino"), pk=ajuste_id
    )
    if request.method == "POST":
        caso = caso_de_ajuste(ua.AnularAjuste)
        motivo = request.POST.get("motivo", "")
        if _intentar(request, lambda: caso.ejecutar(request.actor, ajuste_id, motivo)):
            messages.success(request, "Ajuste anulado.")
            return redirect("ajuste", ajuste_id=ajuste_id)
    contexto = {
        "ajuste": fila,
        "lineas": fila.lineas.select_related("producto__unidad"),
        "movimientos": Movimiento.objects.filter(ref_tipo=ua.REF, ref_id=ajuste_id)
        .select_related("producto", "almacen", "lote")
        .order_by("id"),
        "puede_anular": request.actor.puede(ua.ANULAR) and fila.estado != ua.ANULADO,
        "migas": MIGAS + [("Ajustes", "/inventario/ajustes/"), (f"N.° {fila.numero}", None)],
    }
    return render(request, "inventory/ajuste.html", contexto)


STOCK, KARDEX, COSTO = "inventario.stock.ver", "inventario.kardex.ver", "inventario.costo.ver"
FILTROS_STOCK = ("q", "casilla", "almacen", "categoria", "stock_bajo", "con_stock")
FILTROS_KARDEX = ("producto", "almacen", "lote", "motivo", "desde", "hasta")
MOTIVOS = [  # tipos de movimiento del kardex (0003a, 0003b; compras, OP y ventas después)
    ("SALDO_INICIAL", "Saldo inicial"),
    ("COMPRA", "Compra"),
    ("CONSUMO_OP", "Consumo de OP"),
    ("VENTA", "Venta"),
    ("MERMA", "Merma"),
    ("CONTEO", "Conteo"),
    ("CORRECCION", "Corrección"),
    ("TRANSFERENCIA", "Transferencia"),
    ("ANULACION", "Anulación"),
]


@requiere(STOCK)
def stock(request):
    """Stock por producto con detalle por almacén y lote (RF-INV-04, 05, 16)."""
    filtro = {k: request.GET.get(k, "") for k in FILTROS_STOCK}
    filas, por_categoria, total = consultas.stock(filtro)
    casillas = [(c, c.replace("_", " ").capitalize()) for c in consultas.CASILLAS]
    almacenes, categorias = Almacen.objects.order_by("nombre"), Categoria.objects.order_by("nombre")
    campos = {  # chips de filtros aplicados (docs/ux.md §3)
        "q": ("Búsqueda", None),
        "almacen": ("Almacén", {str(a.id): a.nombre for a in almacenes}),
        "categoria": ("Categoría", {str(c.id): c.nombre for c in categorias}),
        "casilla": ("Gestión", dict(casillas)),
        "stock_bajo": ("Solo stock bajo", None),
        "con_stock": ("Solo con stock", None),
    }
    contexto = {
        "pagina": listados.paginar(request, filas),
        "consulta": listados.consulta(request),
        "aplicados": listados.aplicados(request, campos),
        "por_categoria": por_categoria,
        "total": total,
        "filtro": filtro,
        "ver_costos": request.actor.puede(COSTO),  # RF-TEN-51
        "hoy": timezone.localdate(),
        "casillas": casillas,
        "almacenes": almacenes,
        "categorias": categorias,
        "migas": MIGAS + [("Stock", None)],
    }
    return render(request, "inventory/stock.html", contexto)


ENCABEZADO = ["fecha", "tipo", "motivo", "documento", "producto", "almacen", "lote", "cantidad"]
COSTOS = ["costo_unitario", "costo_total"]
SALDOS = ["saldo", "promedio"]


def _documento(m):
    return f"{m.ref_tipo} {m.ref_id}" if m.ref_id else m.ref_tipo


@requiere(KARDEX)
def kardex(request):
    """Kardex con filtros y cursor; saldos solo con producto (RF-INV-06, 07)."""
    filtro = {k: request.GET.get(k, "") for k in FILTROS_KARDEX}
    ver_costos, con_producto = request.actor.puede(COSTO), filtro["producto"].isdigit()
    if request.GET.get("formato") == "csv":
        respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
        respuesta["Content-Disposition"] = 'attachment; filename="kardex.csv"'
        escritor = csv.writer(respuesta)
        escritor.writerow(
            ENCABEZADO + (COSTOS if ver_costos else []) + (SALDOS if con_producto else [])
        )
        for m in consultas.kardex(filtro, limite=None).iterator():
            fila = [timezone.localtime(m.fecha).isoformat(timespec="seconds"), m.tipo, m.motivo]
            fila += [
                _documento(m),
                m.producto.sku,
                m.almacen.nombre,
                m.lote.codigo if m.lote else "",
            ]
            fila += [m.cantidad] + ([m.costo_unitario, m.costo_total] if ver_costos else [])
            if con_producto:
                fila += [m.saldo_cantidad] + ([m.saldo_promedio] if ver_costos else [""])
            escritor.writerow(fila)
        return respuesta
    despues = request.GET.get("despues", "")
    movimientos = consultas.kardex(filtro, int(despues) if despues.isdigit() else None)
    productos = Producto.objects.filter(tipo="BIEN").order_by("nombre")
    almacenes = Almacen.objects.order_by("nombre")
    contexto = {
        "movimientos": movimientos,
        "filtro": filtro,
        "ver_costos": ver_costos,
        "con_producto": con_producto,
        "siguiente": movimientos[-1].id if len(movimientos) == 50 else None,
        "consulta": urlencode({k: v for k, v in filtro.items() if v}),
        "aplicados": listados.aplicados(
            request,
            {
                "producto": ("Producto", {str(p.id): p.sku for p in productos}),
                "motivo": ("Tipo", dict(MOTIVOS)),
                "almacen": ("Almacén", {str(a.id): a.nombre for a in almacenes}),
                "lote": ("Lote", None),
                "desde": ("Desde", None),
                "hasta": ("Hasta", None),
            },
        ),
        "motivos": MOTIVOS,
        "productos": productos,
        "almacenes": almacenes,
        "migas": MIGAS + [("Kardex", None)],
    }
    return render(request, "inventory/kardex.html", contexto)


@requiere(uc.GESTIONAR)
def configuracion(request):
    """Días de alerta de vencimiento (RF-INV-15)."""
    if request.method == "POST":
        dias = request.POST.get("dias", "")
        caso = caso_de_uso(uc.GuardarDiasAlerta)
        if _intentar(request, lambda: caso.ejecutar(request.actor, int(dias or 0))):
            messages.success(request, "Cambio guardado.")
            return redirect(request.path)
    contexto = {"dias": consultas.dias_alerta(), "migas": MIGAS + [("Configuración", None)]}
    return render(request, "inventory/configuracion.html", contexto)


def aviso_stock_bajo(request):
    filas = consultas.bajo_minimo_productos()
    return render_to_string("inventory/_aviso_stock_bajo.html", {"filas": filas})


def aviso_por_vencer(request):
    lotes = consultas.lotes_en_alerta(timezone.localdate())
    return render_to_string("inventory/_aviso_por_vencer.html", {"lotes": lotes})
