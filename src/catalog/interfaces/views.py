"""Pantallas del catálogo (plan 0002a §5)."""

from dataclasses import asdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from catalog.application import isc as uc_isc
from catalog.application import productos as uc
from catalog.application.puertos import puertos
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.contenedor import caso_de_isc, caso_de_uso
from catalog.infrastructure.models import Familia, IscCategoria, Producto, Unidad
from catalog.infrastructure.repositorios import CatalogoOrm
from catalog.interfaces.forms import ProductoForm
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

POR_PAGINA = 25  # RF-CAT-14


def _form(request, tipo, inicial=None, bloqueados=()):
    unidades = Unidad.objects.filter(activo=True).values_list("abreviatura", flat=True)
    familias = Familia.objects.filter(activo=True).values_list("id", "nombre")
    activos = Producto.objects.filter(activo=True).order_by("nombre")
    datos = request.POST if request.method == "POST" else None
    return ProductoForm(
        datos,
        initial=inicial,
        tipo=tipo,
        unidades=list(unidades),
        familias=list(familias),
        bloqueados=bloqueados,
        graneles=list(activos.filter(tipo=TipoProducto.GRANEL).values_list("id", "nombre")),
        envases=list(activos.filter(tipo=TipoProducto.ENVASE).values_list("id", "nombre")),
        categorias_isc=list(IscCategoria.objects.filter(activo=True).values_list("id", "nombre")),
    )


@requiere("catalogo.producto.ver")
def productos(request):
    g = request.GET
    filas = Producto.objects.select_related("unidad", "familia").order_by("nombre")
    if q := g.get("q", "").strip():
        filas = filas.filter(sku__icontains=q) | filas.filter(nombre__icontains=q)
    if g.get("tipo"):
        filas = filas.filter(tipo=g["tipo"])
    if g.get("familia"):
        filas = filas.filter(familia_id=g["familia"])
    estado = g.get("estado", "activos")
    if estado != "todos":
        filas = filas.filter(activo=estado == "activos")
    if g.get("stock_bajo"):
        # ponytail: recorre los productos con mínimo; la épica 0003 lo resuelve con SQL.
        bajos = [
            p.id
            for p in filas.filter(stock_minimo__gt=0)
            if puertos.inventario.stock(p.id) < p.stock_minimo
        ]
        filas = filas.filter(pk__in=bajos)
    pagina = Paginator(filas, POR_PAGINA).get_page(g.get("pagina"))
    contexto = {
        "pagina": pagina,
        "tipos": list(TipoProducto),
        "familias": Familia.objects.order_by("nombre"),
        "filtro": {k: g.get(k, "") for k in ("q", "tipo", "familia", "stock_bajo")}
        | {"estado": estado},
        "consulta": g.copy().urlencode()
        if "pagina" not in g
        else "&".join(f"{k}={v}" for k, v in g.items() if k != "pagina"),
    }
    return render(request, "catalog/productos.html", contexto)


@requiere("catalogo.producto.gestionar")
def producto_nuevo(request):
    tipo = TipoProducto(request.GET.get("tipo") or TipoProducto.INSUMO)
    form = _form(request, tipo)
    if request.method == "POST" and form.is_valid():
        caso, nuevo = caso_de_uso(uc.CrearProducto), {}
        datos, presentacion = form.datos(), form.presentacion()
        if _intentar(
            request, lambda: nuevo.update(id=caso.ejecutar(request.actor, datos, presentacion))
        ):
            messages.success(request, "Producto creado.")
            return redirect("producto", producto_id=nuevo["id"])
    contexto = {"form": form, "tipo": tipo, "tipos": list(TipoProducto)}
    return render(request, "catalog/producto_form.html", contexto)


@requiere("catalogo.producto.ver")
def producto(request, producto_id):
    datos = CatalogoOrm().producto(producto_id)  # 404 si es de otra empresa
    movimientos = puertos.inventario.tiene_movimientos(producto_id)
    bloqueados = ("sku", "unidad", "controla_lote") if movimientos else ()
    repo = CatalogoOrm()
    inicial = asdict(datos) | {"familia": datos.familia_id or ""}
    inicial |= ProductoForm.inicial_presentacion(repo.presentacion(producto_id))
    form = _form(request, datos.tipo, inicial, bloqueados)
    if request.method == "POST":
        accion, actor = request.POST.get("accion", "guardar"), request.actor
        if accion == "guardar" and form.is_valid():
            caso = caso_de_uso(uc.EditarProducto)
            datos_form, presentacion = form.datos(), form.presentacion()
            hecho = _intentar(
                request, lambda: caso.ejecutar(actor, producto_id, datos_form, presentacion)
            )
        elif accion in ("activar", "desactivar"):
            caso = caso_de_uso(uc.CambiarEstadoProducto)
            activo = accion == "activar"
            hecho = _intentar(request, lambda: caso.ejecutar(actor, producto_id, activo))
        elif accion == "eliminar":
            caso = caso_de_uso(uc.EliminarProducto)
            if _intentar(request, lambda: caso.ejecutar(actor, producto_id)):
                messages.success(request, "Producto eliminado.")
                return redirect("productos")
            hecho = False
        else:
            hecho = False
        if hecho:
            messages.success(request, "Cambio guardado.")
            return redirect("producto", producto_id=producto_id)
    contexto = {
        "form": form,
        "producto": datos,
        "producto_id": producto_id,
        "movimientos": movimientos,
        "stock": puertos.inventario.stock(producto_id),
    }
    return render(request, "catalog/producto.html", contexto)


@requiere("catalogo.unidad.gestionar")
def unidades(request):
    if request.method == "POST":
        p, actor = request.POST, request.actor
        accion = p.get("accion")
        if accion == "crear":
            caso = caso_de_uso(uc.CrearUnidad)
            hecho = _intentar(
                request,
                lambda: caso.ejecutar(actor, p["nombre"], p["abreviatura"], p["codigo_sunat"]),
            )
        elif accion in ("activar", "desactivar"):
            caso = caso_de_uso(uc.CambiarEstadoUnidad)
            hecho = _intentar(
                request, lambda: caso.ejecutar(actor, int(p["unidad"]), accion == "activar")
            )
        else:
            caso = caso_de_uso(uc.EliminarUnidad)
            hecho = _intentar(request, lambda: caso.ejecutar(actor, int(p["unidad"])))
        if hecho:
            messages.success(request, "Cambio guardado.")
            return redirect("unidades")
    filas = Unidad.objects.order_by("abreviatura")
    return render(request, "catalog/unidades.html", {"unidades": filas})


@requiere("catalogo.producto.gestionar")
def familias(request):
    if request.method == "POST":
        caso = caso_de_uso(uc.CrearFamilia)
        if _intentar(request, lambda: caso.ejecutar(request.actor, request.POST.get("nombre", ""))):
            messages.success(request, "Familia creada.")
            return redirect("familias")
    return render(
        request, "catalog/familias.html", {"familias": Familia.objects.order_by("nombre")}
    )


def _monto_y_fecha(p) -> tuple[Decimal | None, date | None]:
    try:
        monto = Decimal(p.get("monto", ""))
    except InvalidOperation:
        monto = None
    return monto, date.fromisoformat(p["desde"]) if p.get("desde") else None


@requiere("catalogo.isc.gestionar")
def isc(request):
    """Categorías con su historial de tarifas; solo se agregan tarifas (RF-CAT-22 a 24, 28)."""
    if request.method == "POST":
        p, actor = request.POST, request.actor
        accion = p.get("accion")

        if accion == "crear":
            caso = caso_de_isc(uc_isc.CrearCategoriaIsc)
            hecho = _intentar(
                request,
                lambda: caso.ejecutar(
                    actor, p["nombre"], p["codigo_tipo_sistema"], *_monto_y_fecha(p)
                ),
            )
        elif accion == "tarifa":
            caso = caso_de_isc(uc_isc.AgregarTarifaIsc)
            hecho = _intentar(
                request, lambda: caso.ejecutar(actor, int(p["categoria"]), *_monto_y_fecha(p))
            )
        else:
            caso = caso_de_isc(uc_isc.CambiarEstadoCategoriaIsc)
            activo = accion == "activar"
            hecho = _intentar(request, lambda: caso.ejecutar(actor, int(p["categoria"]), activo))
        if hecho:
            messages.success(request, "Cambio guardado.")
            return redirect("isc")
    categorias = IscCategoria.objects.prefetch_related("tarifas").order_by("nombre")
    return render(request, "catalog/isc.html", {"categorias": categorias})
