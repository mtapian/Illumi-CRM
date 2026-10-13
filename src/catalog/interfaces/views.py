"""Pantallas del catálogo (plan 0002a §5)."""

from collections import defaultdict
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalog.application import impuestos as uc_impuestos
from catalog.application import productos as uc
from catalog.application.puertos import puertos
from catalog.domain.errores import ImpuestoInvalido
from catalog.domain.producto import CASILLAS
from catalog.domain.receta import contenido_sugerido
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.contenedor import caso_de_impuestos, caso_de_uso, catalogo_query
from catalog.infrastructure.models import Categoria, Impuesto, Marca, Producto, Unidad
from catalog.infrastructure.repositorios import CatalogoOrm
from catalog.interfaces.forms import IMPUESTOS, ProductoForm
from catalog.interfaces.pestanas import pestanas
from shared.domain.vigencia import SinValorVigente, valor_vigente
from shared.interfaces import listados
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

POR_PAGINA = 25  # RF-CAT-14


def _opciones(modelo, actual=None):
    """Activas más la que ya tiene el producto, aunque esté inactiva (RF-CAT-33)."""
    filas = modelo.objects.filter(Q(activo=True) | Q(pk=actual)).order_by("nombre")
    return list(filas.values_list("id", "nombre"))


def _impuestos(tipo, actuales):
    """Activos de un tipo más los que ya tiene el producto, aunque estén inactivos."""
    filas = Impuesto.objects.filter(Q(activo=True) | Q(pk__in=actuales), tipo=tipo)
    return list(filas.order_by("nombre").values_list("id", "nombre"))


def _form(request, inicial=None, bloqueados=(), producto_id=None):
    inicial = inicial or {}
    repo = CatalogoOrm()
    for tipo in ("VENTA", "COMPRA"):  # RF-CAT-56: lo guardado o, si es nuevo, el IGV
        campo = f"impuestos_{tipo.lower()}"
        if campo not in inicial:
            actuales = repo.impuestos_de(producto_id, tipo) if producto_id else None
            defecto = repo.impuesto_por_defecto(tipo)
            inicial[campo] = actuales if actuales is not None else ([defecto] if defecto else [])
        inicial[campo] = [str(i) for i in inicial[campo]]
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
        impuestos_venta=_impuestos("VENTA", [int(i) for i in inicial["impuestos_venta"]]),
        impuestos_compra=_impuestos("COMPRA", [int(i) for i in inicial["impuestos_compra"]]),
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
            if puertos.inventario.stock(p.id) <= p.stock_minimo  # RF-INV-14
        ]
        filas = filas.filter(pk__in=bajos)
    categorias = Categoria.objects.order_by("nombre")
    marcas = Marca.objects.order_by("nombre")
    casillas = [(c, c.replace("_", " ").capitalize()) for c in CASILLAS]
    campos = {  # chips de filtros aplicados (docs/ux.md §3)
        "q": ("Búsqueda", None),
        "tipo": ("Tipo", {t: t.lower().capitalize() for t in TipoProducto}),
        "estado": ("Estado", {"inactivos": "Inactivos", "todos": "Todos"}),
        "casilla": ("Gestión", dict(casillas)),
        "categoria": ("Categoría", {str(c.id): c.nombre for c in categorias}),
        "marca": ("Marca", {str(m.id): m.nombre for m in marcas}),
        "stock_bajo": ("Solo stock bajo", None),
    }
    contexto = {
        "pagina": listados.paginar(request, filas, POR_PAGINA),
        "tipos": list(TipoProducto),
        "categorias": categorias,
        "marcas": marcas,
        "casillas": casillas,
        "filtro": {
            k: g.get(k, "") for k in ("q", "tipo", "casilla", "categoria", "marca", "stock_bajo")
        }
        | {"estado": estado},
        "consulta": listados.consulta(request),
        "aplicados": listados.aplicados(request, campos, {"estado": "activos"}),
        "migas_productos": [("Inicio", "/"), ("Productos", None)],
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
        datos, receta = form.datos(), form.receta()
        listas = {c: form.impuestos(c) for c in IMPUESTOS}
        if _intentar(
            request, lambda: nuevo.update(id=caso.ejecutar(request.actor, datos, receta, **listas))
        ):
            messages.success(request, "Producto creado.")
            return redirect("producto", producto_id=nuevo["id"])
    _errores_al_form(request, form)
    contexto = {"form": form}
    return render(request, "catalog/producto_form.html", contexto | _pestanas(form))


def _errores_al_form(request, form):
    """El error de negocio va junto a su campo y abre su pestaña (docs/ux.md §4)."""
    for campo, mensaje in getattr(request, "errores_campo", {}).items():
        form.add_error(campo if campo in form.fields else None, mensaje)


def _pestanas(form, externas=()):
    """Pestañas propias y externas en orden; abre la primera con errores (RF-CAT-04). Una
    externa puede llevar campos de la ficha (los impuestos de compra van en "Compras")."""
    claves = {p["clave"] for p in externas}
    for p in externas:
        p["campos_ficha"] = form.campos_de(p["clave"], claves)
        p["errores"] = any(f.errors for f in p["campos_ficha"])
    todas = sorted([*form.pestanas(claves), *externas], key=lambda p: p.get("orden", 30))
    abierta = next((p["clave"] for p in todas if p.get("errores")), "general")
    return {"pestanas": todas, "abierta": abierta}


def _sin_permiso_isc(request):
    """Sin `catalogo.isc.gestionar` los impuestos se ven bloqueados (el caso de uso lo exige
    igual en el servidor)."""
    return () if request.actor.puede(uc.ISC) else IMPUESTOS


def _desglose(producto_id, datos):
    """Desglose informativo con los impuestos de venta de hoy (RF-CAT-30, 59)."""
    if not (datos.se_vende and datos.precio_venta):
        return None
    try:
        d = catalogo_query().desglose_de_linea(
            producto_id, datos.precio_venta, Decimal("1"), timezone.localdate()
        )
    except ImpuestoInvalido as e:
        return {"error": e.mensaje}
    return {"precio": datos.precio_venta} | vars(d)


@requiere("catalogo.producto.ver")
def producto(request, producto_id):
    datos = CatalogoOrm().producto(producto_id)  # 404 si es de otra empresa
    movimientos = puertos.inventario.tiene_movimientos(producto_id)
    bloqueados = ("sku", "tipo", "unidad") if movimientos else ()  # RF-CAT-43
    repo = CatalogoOrm()
    receta = repo.receta(producto_id)
    inicial = asdict(datos) | {
        "categoria": datos.categoria_id or "",
        "marca": datos.marca_id or "",
    }
    inicial |= ProductoForm.inicial_receta(receta)
    if datos.contenido_litros is None:  # sugerido desde la receta (informativo)
        unidades = repo.unidades_de([c for c, _ in receta])
        inicial["contenido_litros"] = contenido_sugerido(receta, unidades)
    form = _form(request, inicial, bloqueados + _sin_permiso_isc(request), producto_id)
    if request.method == "POST":
        accion, actor = request.POST.get("accion", "guardar"), request.actor
        if accion == "guardar" and form.is_valid():
            caso = caso_de_uso(uc.EditarProducto)
            datos_form, receta = form.datos(), form.receta()
            listas = {c: form.impuestos(c) for c in IMPUESTOS}
            hecho = _intentar(
                request, lambda: caso.ejecutar(actor, producto_id, datos_form, receta, **listas)
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
    _errores_al_form(request, form)
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
    # Si un "guardar" falló, el formulario vuelve con lo enviado y el error en su campo.
    fallo = request.method == "POST" and request.POST.get("accion") == "guardar"
    if fallo and request.POST.get("id", "").isdigit():
        editar = request.POST["id"]
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
        "nuevo": "nuevo" in request.GET or (fallo and not editando),
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


TIPOS_IMPUESTO = {"VENTA": "Venta", "COMPRA": "Compra"}
CODIGOS_IMPUESTO = {"IGV": "IGV", "EXO": "Exonerado", "INA": "Inafecto", "ISC": "ISC"}
CRITERIOS = {"PORCENTAJE": "Porcentaje (%)", "FIJO": "Monto fijo (S/ por unidad)"}


def _tasa_hoy(impuesto, hoy):
    try:
        return valor_vigente([(t.vigente_desde, t.importe) for t in impuesto.tasas.all()], hoy)
    except SinValorVigente:
        return None


@requiere(uc_impuestos.GESTIONAR)
def impuestos(request):
    """Maestro de impuestos (spec 0002e §5; RF-CAT-53 a 55): listado con filtro por tipo;
    `?editar=<id>` con su historial de tasas y "Agregar tasa"."""
    p, actor, hoy = request.POST, request.actor, timezone.localdate()
    if request.method == "POST":
        id_ = int(p["id"]) if p.get("id", "").isdigit() else None
        guardado = {}
        acciones = {
            "guardar": lambda: guardado.update(
                id=caso_de_impuestos(uc_impuestos.GuardarImpuesto).ejecutar(
                    actor,
                    id_,
                    p.get("nombre", ""),
                    p.get("tipo", ""),
                    p.get("codigo", ""),
                    p.get("criterio") or None,
                )
            ),
            "tasa": lambda: caso_de_impuestos(uc_impuestos.AgregarTasa).ejecutar(
                actor, id_, _decimal(p.get("importe"), "importe"), _fecha(p.get("desde"))
            ),
            "activar": lambda: caso_de_impuestos(uc_impuestos.CambiarEstadoImpuesto).ejecutar(
                actor, id_, True
            ),
            "desactivar": lambda: caso_de_impuestos(uc_impuestos.CambiarEstadoImpuesto).ejecutar(
                actor, id_, False
            ),
        }
        if _intentar(request, acciones.get(p.get("accion"), acciones["guardar"])):
            messages.success(request, "Cambio guardado.")
            if p.get("accion") == "tasa" or (guardado and id_ is None):
                return redirect(f"{request.path}?editar={id_ or guardado['id']}")  # su tasa
            return redirect(request.path)
    todas = (
        Impuesto.objects.annotate(n_productos=Count("productos", distinct=True))
        .prefetch_related("tasas")
        .order_by("tipo", "nombre")
    )
    editar = request.GET.get("editar", "")
    # Si falló, vuelve el formulario (o la ficha, si era una tasa) con lo enviado.
    fallo = request.method == "POST" and p.get("accion") in ("guardar", "tasa")
    if fallo and p.get("id", "").isdigit():
        editar = p["id"]
    editando = get_object_or_404(todas, pk=editar) if editar.isdigit() else None  # art. 3.1
    nuevo = "nuevo" in request.GET or (fallo and not editando)
    filas = todas
    if q := request.GET.get("q", "").strip():
        filas = filas.filter(nombre__icontains=q)
    if (tipo := request.GET.get("tipo", "")) in TIPOS_IMPUESTO:
        filas = filas.filter(tipo=tipo)
    migas = MIGAS_CATALOGO + [("Impuestos", None)]
    if nuevo or editando:
        accion = "Editar" if editando else "Nuevo"
        migas = MIGAS_CATALOGO + [("Impuestos", request.path), (accion, None)]
    valores = {"tipo": "VENTA", "codigo": "IGV"}
    if editando:
        valores |= {
            "nombre": editando.nombre,
            "tipo": editando.tipo,
            "codigo": editando.codigo,
            "criterio": editando.criterio,
        }
    if fallo:
        valores |= {
            k: p.get(k, "") for k in ("nombre", "tipo", "codigo", "criterio", "importe", "desde")
        }
    tasas = (
        sorted(editando.tasas.all(), key=lambda t: t.vigente_desde, reverse=True)
        if editando
        else []
    )
    contexto = {
        "filas": [(f, _tasa_hoy(f, hoy)) for f in filas],
        "q": q,
        "filtro_tipo": tipo,
        "aplicados": listados.aplicados(
            request, {"q": ("Búsqueda", None), "tipo": ("Tipo", TIPOS_IMPUESTO)}
        ),
        "nuevo": nuevo,
        "editando": editando,
        "tasas": tasas,
        "vigente_id": getattr(
            max(
                (t for t in tasas if t.vigente_desde <= hoy),
                key=lambda t: t.vigente_desde,
                default=None,
            ),
            "id",
            None,
        ),
        "valores": valores,
        "tipos": TIPOS_IMPUESTO,
        "codigos": CODIGOS_IMPUESTO,
        "criterios": CRITERIOS,
        "hoy": hoy,
        "migas": migas,
    }
    return render(request, "catalog/impuestos.html", contexto)


def _decimal(texto, campo):
    try:
        return Decimal(texto or "")
    except ArithmeticError:
        raise ImpuestoInvalido("Ingresa un importe válido", campo) from None


def _fecha(texto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        raise ImpuestoInvalido("Ingresa la fecha de vigencia", "desde") from None
