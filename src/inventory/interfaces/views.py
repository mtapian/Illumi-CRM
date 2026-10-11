"""Pantallas del inventario (plan 0003a §5)."""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from inventory.application import almacenes as uc
from inventory.infrastructure.contenedor import caso_de_uso
from inventory.infrastructure.models import Almacen
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
