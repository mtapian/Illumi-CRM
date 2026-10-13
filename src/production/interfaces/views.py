"""Pantallas de órdenes de producción (plan 0005a §5)."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalog.application import productos as uc_productos
from catalog.infrastructure.contenedor import caso_de_uso as caso_de_catalogo
from catalog.infrastructure.models import Producto
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen, Movimiento
from production.application import ordenes as uc
from production.domain import op as dom
from production.domain.errores import OpInvalida
from production.infrastructure.contenedor import caso_de_op
from production.infrastructure.models import OrdenProduccion
from production.infrastructure.repositorios import OrdenesOrm
from shared.interfaces import listados
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

VER, REPORTE, COSTOS = "produccion.op.ver", "produccion.reporte.ver", "inventario.costo.ver"
ESTADOS = [(dom.CREADA, "Creada"), (dom.EN_PROCESO, "En proceso"), (dom.FINALIZADA, "Finalizada")]
ESTADOS += [(dom.ANULADA, "Anulada")]
FILTROS = ("estado", "producto", "desde", "hasta", "q")
CAMPOS_COMPONENTE = ("componente", "por_consumir", "costo")  # "cantidad" es de la cabecera
MIGAS = [("Inicio", "/"), ("Producción", "/produccion/")]


def numero_op(n: int) -> str:
    return f"OP-{n:06d}"


def _id(texto):
    return int(texto) if texto and str(texto).isdigit() else None


def _decimal(texto, campo, nombre, vacio=None):
    if texto in (None, ""):
        return vacio
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise OpInvalida(f"{campo} no es un número válido", nombre) from None


def _fecha(texto, campo, nombre):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise OpInvalida(f"{campo} no es válida", nombre) from None


def _filas(post) -> list[dict]:
    """Componentes enviados, sin límite; cada fila manda todos sus campos (como en compras)."""
    columnas = [post.getlist(c) for c in CAMPOS_COMPONENTE]
    return [dict(zip(CAMPOS_COMPONENTE, v, strict=False)) for v in zip(*columnas, strict=False)]


def _datos(post, con_componentes: bool) -> uc.DatosOp:
    componentes = None
    if con_componentes:
        componentes = tuple(
            dom.Componente(
                int(f["componente"]),
                _decimal(f["por_consumir"], "La cantidad", "componentes", Decimal("0")),
                _decimal(f["costo"], "El costo del servicio", "componentes"),
            )
            for f in _filas(post)
            if f["componente"].isdigit()
        )
    return uc.DatosOp(
        _id(post.get("producto")),
        _decimal(post.get("cantidad"), "La cantidad", "cantidad", Decimal("0")),
        _fecha(post.get("fecha_programada"), "La fecha programada", "fecha_programada"),
        _id(post.get("almacen_origen")),
        _id(post.get("almacen_destino")),
        _id(post.get("responsable")),
        post.get("comentario", ""),
        componentes,
    )


def _opciones() -> dict:
    activos = Producto.objects.filter(activo=True).select_related("unidad").order_by("nombre")
    return {
        "fabricables": activos.filter(tipo="BIEN", se_fabrica=True),
        "productos": activos,
        "almacenes": Almacen.objects.filter(activo=True).order_by("nombre"),
        "responsables": OrdenesOrm().responsables().items(),
    }


def _previstos(orden: list, cantidad: Decimal) -> set[str]:
    """Lotes de los que saldría `cantidad` según la estrategia del producto (lote sugerido)."""
    lotes, falta = set(), cantidad
    for lote, q in orden:
        if falta <= 0:
            break
        if lote:
            lotes.add(lote)
        falta -= q
    return lotes


@requiere(VER)
def ordenes(request):
    """Listado con la grilla estándar (RF-PRD-48; docs/ux.md §5)."""
    filtro = {k: request.GET.get(k, "").strip() for k in FILTROS}
    filas = OrdenProduccion.objects.select_related("producto__unidad", "responsable")
    filas = filas.order_by("-numero")
    if filtro["estado"]:
        filas = filas.filter(estado=filtro["estado"])
    if filtro["producto"].isdigit():
        filas = filas.filter(producto_id=filtro["producto"])
    for campo, condicion in (
        ("desde", "fecha_programada__gte"),
        ("hasta", "fecha_programada__lte"),
    ):
        try:
            filas = filas.filter(**{condicion: date.fromisoformat(filtro[campo])})
        except ValueError:  # vacía o mal escrita: no filtra
            pass
    if q := filtro["q"].upper():
        busca = Q(comentario__icontains=q) | Q(lote_codigo__icontains=q)
        if (n := q.removeprefix("OP-")).isdigit():
            busca |= Q(numero=int(n))
        filas = filas.filter(busca)
    productos = Producto.objects.filter(se_fabrica=True).order_by("nombre")
    campos = {
        "q": ("Búsqueda", None),
        "estado": ("Estado", dict(ESTADOS)),
        "producto": ("Producto", {str(p.id): p.nombre for p in productos}),
        "desde": ("Desde", None),
        "hasta": ("Hasta", None),
    }
    contexto = {
        "pagina": listados.paginar(request, filas),
        "consulta": listados.consulta(request),
        "aplicados": listados.aplicados(request, campos),
        "filtro": filtro,
        "estados": ESTADOS,
        "productos": productos,
        "puede_crear": request.actor.puede(uc.PLANIFICAR),
        "migas": [("Inicio", "/"), ("Producción", None)],
    }
    return render(request, "production/ordenes.html", contexto)


@requiere(uc.PLANIFICAR)
def nueva_op(request):
    """Producto, cantidad, fechas, almacenes, responsable y comentario; con la receta del
    producto si se marca (RF-PRD-35 a 37). Queda Creada, sin stock."""
    if request.method == "POST":
        nuevo = {}

        def crear():
            datos = _datos(request.POST, con_componentes=False)
            usar = request.POST.get("usar_receta") == "on"
            nuevo["id"] = caso_de_op(uc.CrearOp).ejecutar(request.actor, datos, usar)

        if _intentar(request, crear):
            messages.success(request, "OP creada.")
            return redirect("orden", op_id=nuevo["id"])
        valores = request.POST
    else:
        principal = Almacen.objects.filter(activo=True).order_by("id").first()
        almacen = str(principal.id) if principal else ""
        valores = {
            "fecha_programada": timezone.localdate().isoformat(),
            "almacen_origen": almacen,
            "almacen_destino": almacen,
            "responsable": str(request.actor.usuario_id),
            "usar_receta": "on",
        }
    contexto = _opciones() | {"valores": valores, "migas": MIGAS + [("Nueva", None)]}
    return render(request, "production/orden.html", contexto)


def _componentes(fila, hoy, con_disponibilidad: bool) -> list[dict]:
    """Componentes con su disponibilidad en el almacén de origen (RF-PRD-39) y los lotes que
    se sugieren para consumir (RF-PRD-41)."""
    filas = []
    for c in fila.componentes.select_related("producto__unidad").order_by("id"):
        x = {"c": c, "servicio": c.producto.tipo == dom.SERVICIO}
        if con_disponibilidad and not x["servicio"]:
            orden = inventario().existencias_en_orden(c.producto_id, fila.almacen_origen_id, hoy)
            x["disponible"] = sum((q for _, q in orden), Decimal("0")) >= c.por_consumir
            x["lotes"] = orden
            x["previstos"] = _previstos(orden, c.por_consumir)
        if c.consumido is not None:
            x["merma"] = dom.merma(c.por_consumir, c.consumido)
        filas.append(x)
    return filas


def _finalizacion(post, fila) -> uc.Finalizacion:
    consumos = tuple(
        uc.ConsumoReal(
            c.producto_id,
            _decimal(
                post.get(f"consumido_{c.producto_id}"),
                "Lo consumido",
                "componentes",
                c.por_consumir,
            ),
            post.get(f"lote_{c.producto_id}") or None,
        )
        for c in fila.componentes.all()
    )
    vence = post.get("vencimiento")
    return uc.Finalizacion(
        _decimal(post.get("producida"), "La cantidad producida", "producida", Decimal("0")),
        _fecha(post.get("fecha_fin"), "La fecha de fin", "fecha_fin"),
        consumos,
        _decimal(
            post.get("costo_indirecto"), "El costo indirecto", "costo_indirecto", Decimal("0")
        ),
        post.get("lote", "").strip(),
        _fecha(vence, "El vencimiento", "vencimiento") if vence else None,
        post.get("motivo_perdida", ""),
    )


@requiere(VER)
def orden(request, op_id):
    """Ficha: edición mientras esté Creada o En proceso, con la barra de estados; Finalizada o
    Anulada, solo lectura con la pestaña Costos y sus movimientos (RF-PRD-34, 36 a 46)."""
    relacionados = ("producto__unidad", "almacen_origen", "almacen_destino", "responsable")
    relacionados += ("creada_por", "finalizada_por", "anulada_por")
    fila = get_object_or_404(OrdenProduccion.objects.select_related(*relacionados), pk=op_id)
    hoy, actor = timezone.localdate(), request.actor
    if request.method == "POST":
        p = request.POST
        editar = lambda: caso_de_op(uc.EditarOp).ejecutar(actor, op_id, _datos(p, True))  # noqa: E731
        acciones = {
            "guardar": editar,
            "en_proceso": lambda: (
                editar() if actor.puede(uc.PLANIFICAR) else None,
                caso_de_op(uc.PasarAEnProceso).ejecutar(actor, op_id),
            ),
            "finalizar": lambda: avisos.extend(
                caso_de_op(uc.FinalizarOp).ejecutar(actor, op_id, _finalizacion(p, fila), hoy)
            ),
            "anular": lambda: caso_de_op(uc.AnularOp).ejecutar(actor, op_id, p.get("motivo", "")),
            "receta": lambda: caso_de_catalogo(uc_productos.GuardarReceta).ejecutar(
                actor,
                fila.producto_id,
                dom.receta_desde_op(_datos(p, True).componentes, fila.cantidad),
            ),
        }
        avisos = []
        accion = p.get("accion", "guardar")
        if _intentar(request, acciones.get(accion, acciones["guardar"])):
            resultado = {
                "finalizar": "OP finalizada: se consumieron los componentes e ingresó el producto.",
                "en_proceso": "La OP pasó a en proceso.",
                "anular": "OP anulada.",
                "receta": "Los componentes se guardaron como la receta del producto.",
            }
            messages.success(request, resultado.get(accion, "Cambios guardados."))
            for aviso in avisos:
                messages.warning(request, aviso)
            return redirect("orden", op_id=op_id)
    editable = fila.estado in (dom.CREADA, dom.EN_PROCESO) and actor.puede(uc.PLANIFICAR)
    abierta = fila.estado in (dom.CREADA, dom.EN_PROCESO)
    componentes = _componentes(fila, hoy, abierta)
    lotes = {x["c"].producto_id: x.get("previstos", set()) for x in componentes}
    if request.method == "POST" and editable:
        valores, filas = request.POST, _filas(request.POST)
    else:
        valores = {
            "producto": str(fila.producto_id),
            "cantidad": fila.cantidad.normalize(),
            "fecha_programada": fila.fecha_programada.isoformat(),
            "almacen_origen": str(fila.almacen_origen_id),
            "almacen_destino": str(fila.almacen_destino_id),
            "responsable": str(fila.responsable_id or ""),
            "comentario": fila.comentario,
        }
        filas = [
            {
                "componente": str(x["c"].producto_id),
                "por_consumir": x["c"].por_consumir.normalize(),
                "costo": x["c"].costo_servicio if x["c"].costo_servicio is not None else "",
                "x": x,
            }
            for x in componentes
        ]
    ve_costos = actor.puede(REPORTE) and actor.puede(COSTOS)
    contexto = _opciones() | {
        "op": fila,
        "numero": numero_op(fila.numero),
        "estado_texto": dict(ESTADOS)[fila.estado],
        "estados": ESTADOS[:3],
        "editable": editable,
        "valores": valores,
        "filas": filas or [{}],
        "componentes": componentes,
        "puede_ejecutar": abierta and actor.puede(uc.EJECUTAR),
        "puede_anular": abierta and actor.puede(uc.ANULAR),
        "puede_receta": editable and actor.puede(uc_productos.GESTIONAR),
        "ve_costos": ve_costos,
        "rendimiento": dom.rendimiento(fila.cantidad, fila.cantidad_producida)
        if fila.cantidad_producida is not None
        else None,
        "lote_sugerido": dom.sugerir_lote(
            lotes, fila.producto.sku, OrdenesOrm().correlativo_lote(fila.producto_id)
        )
        if abierta
        else "",
        "accion_fallida": request.POST.get("accion", "guardar") if request.method == "POST" else "",
        "hoy": hoy.isoformat(),
        "movimientos": Movimiento.objects.filter(ref_tipo="OP", ref_id=op_id)
        .select_related("producto", "almacen", "lote")
        .order_by("id"),
        "migas": MIGAS + [(numero_op(fila.numero), None)],
    }
    return render(request, "production/orden.html", contexto)
