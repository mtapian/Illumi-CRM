"""Pantallas del inventario (plan 0003a §5)."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.application import ajustes as ua
from inventory.application import almacenes as uc
from inventory.application.ajustes import LineaAjuste
from inventory.domain.ajuste import TIPOS
from inventory.domain.errores import AjusteInvalido
from inventory.infrastructure.contenedor import caso_de_ajuste, caso_de_uso
from inventory.infrastructure.models import Ajuste, Almacen, Movimiento
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
    editando = get_object_or_404(todas, pk=editar) if editar.isdigit() else None  # art. 3.1
    nuevo = "nuevo" in request.GET
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


LINEAS = 10  # plan 0003b §6: líneas fijas en el MVP


def _numero(texto, campo):
    if not texto:
        return None
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise AjusteInvalido(f"{campo} no es un número válido") from None


def _lineas(post) -> list[LineaAjuste]:
    lineas = []
    for i in range(LINEAS):
        producto = post.get(f"producto_{i}", "")
        if not producto.isdigit():
            continue
        vence = post.get(f"vencimiento_{i}")
        lineas.append(
            LineaAjuste(
                int(producto),
                _numero(post.get(f"cantidad_{i}"), "La cantidad") or Decimal("0"),
                _numero(post.get(f"costo_{i}"), "El costo unitario"),
                post.get(f"lote_{i}", "").strip() or None,
                date.fromisoformat(vence) if vence else None,
                post.get(f"sentido_{i}", ""),
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
        "lineas": range(LINEAS),
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
