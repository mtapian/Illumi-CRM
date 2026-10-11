"""Pantallas del catálogo (plan 0002a §5)."""

from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalog.application import productos as uc
from catalog.application.puertos import puertos
from catalog.domain.errores import IscSinTarifaVigente
from catalog.domain.isc import contenido_sugerido, tarifa_aplicable
from catalog.domain.precio import desglose_precio
from catalog.domain.producto import CASILLAS
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.contenedor import caso_de_uso, catalogo_query
from catalog.infrastructure.models import Categoria, Marca, Producto, Unidad
from catalog.infrastructure.repositorios import CatalogoOrm
from catalog.interfaces.forms import ProductoForm
from catalog.interfaces.pestanas import pestanas
from tenancy.infrastructure.contenedor import tenancy_service
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

POR_PAGINA = 25  # RF-CAT-14


def _opciones(modelo, actual=None):
    """Activas más la que ya tiene el producto, aunque esté inactiva (RF-CAT-33)."""
    filas = modelo.objects.filter(Q(activo=True) | Q(pk=actual)).order_by("nombre")
    return list(filas.values_list("id", "nombre"))


def _form(request, inicial=None, bloqueados=(), producto_id=None):
    inicial = inicial or {}
    unidades = (
        Unidad.objects.filter(activo=True).order_by("nombre").values_list("abreviatura", "nombre")
    )
    # Componentes de la receta: cualquier producto activo menos el propio (RF-CAT-41).
    activos = Producto.objects.filter(activo=True).exclude(pk=producto_id).order_by("nombre")
    datos = request.POST if request.method == "POST" else None
    return ProductoForm(
        datos,
        initial=inicial,
        unidades=list(unidades),
        categorias=_opciones(Categoria, inicial.get("categoria_id")),
        marcas=_opciones(Marca, inicial.get("marca_id")),
        bloqueados=bloqueados,
        componentes=[(i, f"{s} · {n}") for i, s, n in activos.values_list("id", "sku", "nombre")],
    )


@requiere("catalogo.producto.ver")
def productos(request):
    g = request.GET
    filas = Producto.objects.select_related("unidad", "categoria", "marca").order_by("nombre")
    if q := g.get("q", "").strip():
        filas = filas.filter(sku__icontains=q) | filas.filter(nombre__icontains=q)
    if g.get("tipo"):
        filas = filas.filter(tipo=g["tipo"])
    if g.get("casilla") in CASILLAS:
        filas = filas.filter(**{g["casilla"]: True})
    if g.get("categoria"):
        filas = filas.filter(categoria_id=g["categoria"])
    if g.get("marca"):
        filas = filas.filter(marca_id=g["marca"])
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
        "categorias": Categoria.objects.order_by("nombre"),
        "marcas": Marca.objects.order_by("nombre"),
        "casillas": [(c, c.replace("_", " ").capitalize()) for c in CASILLAS],
        "filtro": {
            k: g.get(k, "") for k in ("q", "tipo", "casilla", "categoria", "marca", "stock_bajo")
        }
        | {"estado": estado},
        "consulta": g.copy().urlencode()
        if "pagina" not in g
        else "&".join(f"{k}={v}" for k, v in g.items() if k != "pagina"),
    }
    return render(request, "catalog/productos.html", contexto)


@requiere("catalogo.producto.gestionar")
def producto_nuevo(request):
    # RF-CAT-38: un bien nuevo se compra; un servicio (`?tipo=SERVICIO`) se vende, en SERV.
    servicio = request.GET.get("tipo") == TipoProducto.SERVICIO
    inicial = {"tipo": TipoProducto.BIEN, "unidad": "UND", "se_compra": True}
    if servicio:
        inicial = {"tipo": TipoProducto.SERVICIO, "unidad": "SERV", "se_vende": True}
        inicial["se_compra"] = False
    form = _form(request, inicial, _sin_permiso_isc(request))
    if request.method == "POST" and form.is_valid():
        caso, nuevo = caso_de_uso(uc.CrearProducto), {}
        datos, receta, tasa = form.datos(), form.receta(), form.tasa()
        if _intentar(
            request,
            lambda: nuevo.update(id=caso.ejecutar(request.actor, datos, receta, tasa)),
        ):
            messages.success(request, "Producto creado.")
            return redirect("producto", producto_id=nuevo["id"])
    contexto = {"form": form}
    return render(request, "catalog/producto_form.html", contexto | _pestanas(form))


def _pestanas(form, externas=()):
    """Pestañas propias y externas en orden; abre la primera con errores (RF-CAT-04)."""
    todas = sorted([*form.pestanas(), *externas], key=lambda p: p.get("orden", 30))
    abierta = next((p["clave"] for p in todas if p.get("errores")), "general")
    return {"pestanas": todas, "abierta": abierta}


ISC_CAMPOS = ("afecto_isc", "isc_codigo_tipo_sistema", "contenido_litros", "tasa_monto")
ISC_CAMPOS += ("tasa_desde",)


def _sin_permiso_isc(request):
    """Sin `catalogo.isc.gestionar` los campos de ISC se ven bloqueados (el caso de uso lo
    exige igual en el servidor)."""
    return () if request.actor.puede(uc.ISC) else ISC_CAMPOS


def _tasas(tasas):
    """Historial de tasas, de la más reciente a la más antigua, marcando la vigente hoy."""
    vigente = tarifa_aplicable(tasas, timezone.localdate())
    return [{"t": t, "vigente": t == vigente} for t in tasas]


def _desglose(producto_id, datos):
    """Desglose informativo con el IGV y el ISC de hoy (RF-CAT-30)."""
    if not (datos.se_vende and datos.precio_venta):
        return None
    hoy = timezone.localdate()
    try:
        isc = catalogo_query().isc_de_linea(producto_id, Decimal("1"), hoy)
    except IscSinTarifaVigente as e:
        return {"error": str(e)}
    igv = tenancy_service().igv_vigente(hoy)
    return {"precio": datos.precio_venta, "igv_pct": igv} | vars(
        desglose_precio(datos.precio_venta, igv, isc)
    )


@requiere("catalogo.producto.ver")
def producto(request, producto_id):
    datos = CatalogoOrm().producto(producto_id)  # 404 si es de otra empresa
    movimientos = puertos.inventario.tiene_movimientos(producto_id)
    bloqueados = ("sku", "tipo", "unidad") if movimientos else ()  # RF-CAT-43
    if movimientos and datos.afecto_isc:
        bloqueados += ("contenido_litros",)  # RF-CAT-46
    repo = CatalogoOrm()
    receta = repo.receta(producto_id)
    inicial = asdict(datos) | {
        "categoria": datos.categoria_id or "",
        "marca": datos.marca_id or "",
    }
    inicial |= {"afecto_isc": datos.afecto_isc} | ProductoForm.inicial_receta(receta)
    if datos.contenido_litros is None:  # RF-CAT-45: sugerido desde la receta
        unidades = repo.unidades_de([c for c, _ in receta])
        inicial["contenido_litros"] = contenido_sugerido(receta, unidades)
    form = _form(request, inicial, bloqueados + _sin_permiso_isc(request), producto_id)
    if request.method == "POST":
        accion, actor = request.POST.get("accion", "guardar"), request.actor
        if accion == "guardar" and form.is_valid():
            caso = caso_de_uso(uc.EditarProducto)
            datos_form, receta, tasa = form.datos(), form.receta(), form.tasa()
            hecho = _intentar(
                request, lambda: caso.ejecutar(actor, producto_id, datos_form, receta, tasa)
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
    externas = pestanas.para(request, producto_id, form.casillas_activas(), request.actor.permisos)
    gestiona = request.actor.puede(uc.GESTIONAR)
    contexto = {
        "boton": "Guardar" if gestiona else "",
        "form": form,
        "producto": datos,
        "producto_id": producto_id,
        "movimientos": movimientos,
        "stock": puertos.inventario.stock(producto_id),
        "desglose": _desglose(producto_id, datos),
        "historial": repo.historial(producto_id),
        "tasas_isc": _tasas(repo.tasas_isc(producto_id)),
    }
    return render(request, "catalog/producto.html", contexto | _pestanas(form, externas))


MIGAS_CATALOGO = [("Inicio", "/"), ("Catálogo", "/catalogo/productos/")]


def _maestro(request, plantilla, contexto, guardar, estado, eliminar, filas, buscar):
    """Listado de maestro (ADR-12; RF-CAT-36, 51): buscar, activar/desactivar y eliminar;
    `?nuevo=1` y `?editar=<id>` muestran solo el formulario, en su propia página.
    `guardar`, `estado` y `eliminar` reciben (actor, POST)."""
    if request.method == "POST":
        p, actor = request.POST, request.actor
        accion = {"guardar": guardar, "activar": estado, "desactivar": estado}
        hacer = accion.get(p.get("accion"), eliminar)
        if _intentar(request, lambda: hacer(actor, p)):
            messages.success(request, "Cambio guardado.")
            return redirect(request.path)
    q = request.GET.get("q", "").strip()
    todas = filas.annotate(n_productos=Count("productos"))
    editar = request.GET.get("editar", "")
    editando = get_object_or_404(todas, pk=editar) if editar.isdigit() else None
    valores = defaultdict(str, request.POST.dict() if request.method == "POST" else {})
    if editando and request.method != "POST":
        valores |= {
            c: getattr(editando, c, "")
            for c in ("nombre", "abreviatura", "codigo_sunat", "descripcion", "activo")
        }
    contexto |= {
        "filas": todas.filter(buscar(q)) if q else todas,
        "q": q,
        "nuevo": "nuevo" in request.GET,
        # Manager por empresa: un id de otra empresa da 404 (art. 3.1).
        "editando": editando,
        "valores": valores,
        "migas": MIGAS_CATALOGO + [(contexto["titulo"], None)],
    }
    if contexto["nuevo"] or editando:  # RF-CAT-51: el formulario va en su propia página
        accion = "Editar" if editando else "Nueva"
        contexto["migas"] = MIGAS_CATALOGO + [(contexto["titulo"], request.path), (accion, None)]
    return render(request, plantilla, contexto)


def _id(p):
    return int(p["id"]) if p.get("id") else None


@requiere("catalogo.unidad.gestionar")
def unidades(request):
    def guardar(actor, p):
        if _id(p):
            caso = caso_de_uso(uc.EditarUnidad)
            return caso.ejecutar(actor, _id(p), p["nombre"], p["abreviatura"], p["codigo_sunat"])
        caso = caso_de_uso(uc.CrearUnidad)
        return caso.ejecutar(actor, p["nombre"], p["abreviatura"], p["codigo_sunat"])

    return _maestro(
        request,
        "catalog/unidades.html",
        {"titulo": "Unidades de medida", "singular": "unidad", "boton": "Nueva unidad"},
        guardar,
        lambda actor, p: caso_de_uso(uc.CambiarEstadoUnidad).ejecutar(
            actor, _id(p), p["accion"] == "activar"
        ),
        lambda actor, p: caso_de_uso(uc.EliminarUnidad).ejecutar(actor, _id(p)),
        Unidad.objects.order_by("nombre"),
        lambda q: Q(nombre__icontains=q) | Q(abreviatura__icontains=q),
    )


SINGULAR = {"categoria": "categoría", "marca": "marca"}


def _agrupacion(request, tipo, modelo, titulo, boton):
    """Categorías y marcas comparten reglas y pantalla (RF-CAT-33, 34, 50)."""

    def guardar(actor, p):
        # La categoría trae descripción y la casilla "activa" en su formulario (RF-CAT-50).
        extra = {}
        if tipo == "categoria":
            extra = {"descripcion": p.get("descripcion", ""), "activo": p.get("activo") == "on"}
        caso = caso_de_uso(uc.GuardarAgrupacion)
        return caso.ejecutar(actor, tipo, _id(p), p.get("nombre", ""), **extra)

    return _maestro(
        request,
        "catalog/agrupaciones.html",
        {"titulo": titulo, "singular": SINGULAR[tipo], "boton": boton, "tipo": tipo},
        guardar,
        lambda actor, p: caso_de_uso(uc.CambiarEstadoAgrupacion).ejecutar(
            actor, tipo, _id(p), p["accion"] == "activar"
        ),
        lambda actor, p: caso_de_uso(uc.EliminarAgrupacion).ejecutar(actor, tipo, _id(p)),
        modelo.objects.order_by("nombre"),
        lambda q: Q(nombre__icontains=q),
    )


@requiere("catalogo.producto.gestionar")
def categorias(request):
    return _agrupacion(request, "categoria", Categoria, "Categorías", "Nueva categoría")


@requiere("catalogo.producto.gestionar")
def marcas(request):
    return _agrupacion(request, "marca", Marca, "Marcas", "Nueva marca")
