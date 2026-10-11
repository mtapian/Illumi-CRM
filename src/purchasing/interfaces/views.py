"""Pantallas de proveedores y compras (planes 0002d y 0004a §5)."""

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.infrastructure.models import Almacen, Movimiento
from purchasing.application import compras as cc
from purchasing.application import proveedores as uc
from purchasing.application.compras import DatosCompra
from purchasing.application.puertos import puertos
from purchasing.domain.compra import CREADA, DOCUMENTOS, EN_PROCESO, LineaCompra, numero_compra
from purchasing.domain.errores import CompraInvalida, ProveedorInvalido
from purchasing.domain.proveedor import DatosProveedor
from purchasing.infrastructure.contenedor import caso_de_compra, caso_de_uso
from purchasing.infrastructure.models import Compra, Proveedor, ProveedorProducto
from tenancy.infrastructure.contenedor import tenancy_service
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


# --- Compras (spec 0004a) ---

CAMPOS_LINEA = ("producto", "cantidad", "costo", "bonificacion", "lote", "vencimiento")
FILTROS = ("proveedor", "estado", "desde", "hasta", "q")
ESTADOS = [("CREADA", "Creada"), ("EN_PROCESO", "En proceso"), ("FINALIZADA", "Finalizada")]
ESTADOS += [("ANULADA", "Anulada")]
MIGAS_COMPRAS = [("Inicio", "/"), ("Compras", "/compras/")]


def _decimal(texto, campo):
    try:
        return Decimal(texto or "0")
    except InvalidOperation:
        raise CompraInvalida(f"{campo} no es un número válido") from None


def _fecha(texto, campo="La fecha"):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise CompraInvalida(f"{campo} no es válida") from None


def _filas(post) -> list[dict]:
    """Las líneas enviadas, sin límite; cada línea manda todos sus campos (como en ajustes)."""
    columnas = [post.getlist(c) for c in CAMPOS_LINEA]
    return [dict(zip(CAMPOS_LINEA, v, strict=False)) for v in zip(*columnas, strict=False)]


def _datos(post) -> DatosCompra:
    lineas = [
        LineaCompra(
            int(f["producto"]),
            _decimal(f["cantidad"], "La cantidad"),
            _decimal(f["costo"], "El costo unitario"),
            f["bonificacion"] == "si",
            f["lote"].strip() or None,
            _fecha(f["vencimiento"], "El vencimiento") if f["vencimiento"] else None,
        )
        for f in _filas(post)
        if f["producto"].isdigit()
    ]
    return DatosCompra(
        _id(post.get("proveedor")),
        _fecha(post.get("fecha")),
        _id(post.get("almacen")),
        post.get("doc_tipo", ""),
        post.get("doc_serie_numero", ""),
        post.get("observacion", ""),
        lineas,
    )


def _formulario(request, compra=None) -> dict:
    """Lo que necesita el formulario de la compra: si se rechazó, vuelve lo enviado."""
    if request.method == "POST":
        valores, filas = request.POST, _filas(request.POST)
    elif compra:
        valores = {
            "proveedor": str(compra.proveedor_id),
            "fecha": compra.fecha.isoformat(),
            "almacen": str(compra.almacen_id),
            "doc_tipo": compra.doc_tipo,
            "doc_serie_numero": compra.doc_serie_numero,
            "observacion": compra.observacion,
        }
        filas = [
            {
                "producto": str(x.producto_id),
                "cantidad": x.cantidad.normalize(),
                "costo": x.costo_unitario.normalize(),
                "bonificacion": "si" if x.es_bonificacion else "",
                "lote": x.lote_codigo,
                "vencimiento": x.vencimiento.isoformat() if x.vencimiento else "",
            }
            for x in compra.lineas.order_by("id")
        ]
    else:
        valores, filas = {"fecha": timezone.localdate().isoformat()}, []
    return {
        "valores": valores,
        "filas": filas or [{}],
        "documentos": [(k, v.capitalize()) for k, v in DOCUMENTOS.items()],
        "igv": tenancy_service().igv_vigente(timezone.localdate()),  # totales informativos
        "proveedores": Proveedor.objects.filter(activo=True).order_by("razon_social"),
        "almacenes": Almacen.objects.filter(activo=True).order_by("nombre"),
        "productos": Producto.objects.filter(activo=True, tipo="BIEN", se_compra=True)
        .select_related("unidad")
        .order_by("nombre"),
    }


@requiere(cc.VER)
def compras(request):
    """Listado con filtros por proveedor, estado, fechas y número (RF-COM-14)."""
    filtro = {k: request.GET.get(k, "").strip() for k in FILTROS}
    filas = Compra.objects.select_related("proveedor").order_by("-numero")
    if filtro["proveedor"].isdigit():
        filas = filas.filter(proveedor_id=filtro["proveedor"])
    if filtro["estado"]:
        filas = filas.filter(estado=filtro["estado"])
    for campo, condicion in (("desde", "fecha__gte"), ("hasta", "fecha__lte")):
        try:
            filas = filas.filter(**{condicion: date.fromisoformat(filtro[campo])})
        except ValueError:  # vacía o mal escrita: no filtra
            pass
    if q := filtro["q"].upper():  # número C-000001, serie-número del documento o guía
        busca = Q(doc_serie_numero__icontains=q) | Q(guia_remision__icontains=q)
        if (n := q.removeprefix("C-")).isdigit():
            busca |= Q(numero=int(n))
        filas = filas.filter(busca)
    contexto = {
        "filas": filas[:200],
        "filtro": filtro,
        "estados": ESTADOS,
        "proveedores": Proveedor.objects.order_by("razon_social"),
        "puede_registrar": request.actor.puede(cc.REGISTRAR),
        "migas": MIGAS,
    }
    return render(request, "purchasing/compras.html", contexto)


@requiere(cc.REGISTRAR)
def nueva_compra(request):
    """Cabecera y líneas dinámicas; queda Creada, sin stock (RF-COM-04)."""
    if request.method == "POST":
        nuevo = {}

        def crear():
            nuevo["id"] = caso_de_compra(cc.CrearCompra).ejecutar(
                request.actor, _datos(request.POST)
            )

        if _intentar(request, crear):
            messages.success(request, "Compra creada.")
            return redirect("compra", compra_id=nuevo["id"])
    contexto = _formulario(request) | {"migas": MIGAS_COMPRAS + [("Nueva", None)]}
    return render(request, "purchasing/compra.html", contexto)


@requiere(cc.VER)
def compra(request, compra_id):
    """Edición mientras no esté Finalizada, con la barra de estados (RF-COM-25 a 27); si no,
    detalle de solo lectura con sus movimientos de kardex (RF-COM-13, 14)."""
    relacionados = ("proveedor", "almacen", "usuario", "finalizada_por")
    fila = get_object_or_404(Compra.objects.select_related(*relacionados), pk=compra_id)
    if request.method == "POST":
        p, actor = request.POST, request.actor
        acciones = {
            "guardar": lambda: caso_de_compra(cc.EditarCompra).ejecutar(
                actor, compra_id, _datos(p)
            ),
            "en_proceso": lambda: (  # guarda lo editado y la pasa a en proceso
                caso_de_compra(cc.EditarCompra).ejecutar(actor, compra_id, _datos(p)),
                caso_de_compra(cc.PasarAEnProceso).ejecutar(actor, compra_id),
            ),
            "finalizar": lambda: caso_de_compra(cc.FinalizarCompra).ejecutar(
                actor,
                compra_id,
                _id(p.get("almacen_recepcion")),
                _fecha(p.get("fecha_recepcion"), "La fecha de recepción"),
                p.get("guia", ""),
                timezone.localdate(),
            ),
        }
        if _intentar(request, acciones.get(p.get("accion"), acciones["guardar"])):
            final = p.get("accion") == "finalizar"
            messages.success(request, "Compra finalizada." if final else "Cambio guardado.")
            return redirect("compra", compra_id=compra_id)
    editable = fila.estado in (CREADA, EN_PROCESO) and request.actor.puede(cc.REGISTRAR)
    contexto = (_formulario(request, fila) if editable else {}) | {
        "compra": fila,
        "numero": numero_compra(fila.numero),
        "editable": editable,
        "estados": ESTADOS[:3],
        "hoy": timezone.localdate().isoformat(),
        "lineas": fila.lineas.select_related("producto__unidad").order_by("id"),
        "movimientos": Movimiento.objects.filter(ref_tipo=cc.REF, ref_id=compra_id)
        .select_related("producto", "almacen", "lote")
        .order_by("id"),
        "migas": MIGAS_COMPRAS + [(numero_compra(fila.numero), None)],
    }
    return render(request, "purchasing/compra.html", contexto)
