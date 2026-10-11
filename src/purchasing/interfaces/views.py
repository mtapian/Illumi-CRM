"""Pantallas de proveedores (plan 0002d §5)."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from purchasing.application import proveedores as uc
from purchasing.application.puertos import puertos
from purchasing.domain.errores import ProveedorInvalido
from purchasing.domain.proveedor import DatosProveedor
from purchasing.infrastructure.contenedor import caso_de_uso
from purchasing.infrastructure.models import Proveedor, ProveedorProducto
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

CAMPOS = ("tipo_doc", "num_doc", "razon_social", "contacto", "telefono", "email", "direccion")
MIGAS = [("Inicio", "/"), ("Compras", None)]


def _id(texto):
    return int(texto) if texto and texto.isdigit() else None


@requiere(uc.GESTIONAR)
def proveedores(request):
    """Listado de maestro (ADR-12; RF-COM-01 a 03); `?nuevo=1` y `?editar=<id>` abren el
    formulario en su propia página (RF-CAT-51)."""
    if request.method == "POST":
        p, actor, id_ = request.POST, request.actor, _id(request.POST.get("id"))
        acciones = {
            "guardar": lambda: caso_de_uso(uc.GuardarProveedor).ejecutar(
                actor, id_, DatosProveedor(*(p.get(c, "") for c in CAMPOS))
            ),
            "activar": lambda: caso_de_uso(uc.CambiarEstadoProveedor).ejecutar(actor, id_, True),
            "desactivar": lambda: caso_de_uso(uc.CambiarEstadoProveedor).ejecutar(
                actor, id_, False
            ),
            "eliminar": lambda: caso_de_uso(uc.EliminarProveedor).ejecutar(actor, id_),
        }
        if _intentar(request, acciones.get(p.get("accion"), acciones["eliminar"])):
            messages.success(request, "Cambio guardado.")
            return redirect(request.path)
    todas = Proveedor.objects.annotate(n_productos=Count("productos")).order_by("razon_social")
    q = request.GET.get("q", "").strip()
    filas = todas.filter(Q(razon_social__icontains=q) | Q(num_doc__icontains=q)) if q else todas
    editar = request.GET.get("editar", "")
    editando = get_object_or_404(todas, pk=editar) if editar.isdigit() else None  # art. 3.1
    valores = defaultdict(str, request.POST.dict() if request.method == "POST" else {})
    if editando and request.method != "POST":
        valores |= {c: getattr(editando, c) for c in CAMPOS}
    nuevo = "nuevo" in request.GET
    migas = MIGAS + [("Proveedores", None)]
    if nuevo or editando:
        migas = MIGAS + [("Proveedores", request.path), ("Editar" if editando else "Nuevo", None)]
    contexto = {
        "filas": [(f, puertos.compras.tiene_compras(f.id)) for f in filas],
        "q": q,
        "nuevo": nuevo,
        "editando": editando,
        "valores": valores,
        "migas": migas,
    }
    return render(request, "purchasing/proveedores.html", contexto)


def pestana_compras(request, producto_id):
    """Pestaña "Compras" de la ficha de producto (RF-COM-22)."""
    contexto = {
        "producto_id": producto_id,
        "filas": ProveedorProducto.objects.filter(producto_id=producto_id)
        .select_related("proveedor")
        .order_by("proveedor__razon_social"),
        "gestiona": request.actor.puede(uc.GESTIONAR),
        "proveedores": Proveedor.objects.filter(activo=True).order_by("razon_social"),
    }
    return render_to_string("purchasing/_pestana_compras.html", contexto, request=request)


def _numero(texto, tipo, mensaje):
    try:
        return tipo(texto)
    except (InvalidOperation, TypeError, ValueError):
        raise ProveedorInvalido(mensaje) from None


@requiere(uc.GESTIONAR)
def proveedor_producto(request):
    """Asocia o quita un proveedor desde la pestaña Compras (RF-COM-21, 22). El producto
    llega en el formulario: el caso de uso lo busca en la empresa actual."""
    if request.method != "POST":
        return redirect("proveedores")
    p, actor = request.POST, request.actor
    proveedor, producto = _id(p.get("proveedor")), _id(p.get("producto"))

    def hacer():
        if p.get("accion") == "quitar":
            return caso_de_uso(uc.QuitarProveedorProducto).ejecutar(actor, proveedor, producto)
        if proveedor is None:
            raise ProveedorInvalido("Elige un proveedor")
        precio = _numero(p.get("precio") or "0", Decimal, "El precio referencial no es válido")
        plazo = _numero(p.get("plazo") or "0", int, "El plazo de entrega no es válido")
        caso = caso_de_uso(uc.AsociarProveedorProducto)
        return caso.ejecutar(actor, proveedor, producto, precio, plazo, p.get("codigo", ""))

    if producto is None:
        return redirect("productos")
    if _intentar(request, hacer):
        messages.success(request, "Cambio guardado.")
    return redirect("producto", producto_id=producto)
