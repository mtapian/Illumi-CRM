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
CAMPOS_COMPONENTE = ("componente", "por_consumir", "costo", "para")  # "para": salida o común
CAMPOS_SALIDA = ("salida_producto", "salida_cantidad", "salida_factor")
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


def _filas(post, campos=CAMPOS_COMPONENTE) -> list[dict]:
    """Filas enviadas, sin límite; cada fila manda todos sus campos (como en compras)."""
    columnas = [post.getlist(c) for c in campos]
    return [dict(zip(campos, v, strict=False)) for v in zip(*columnas, strict=False)]


def _salidas(post) -> tuple[dom.Salida, ...]:
    """Productos de salida (enmienda 1, RF-PRD-49); sin factor, el sugerido por los litros."""
    filas = [f for f in _filas(post, CAMPOS_SALIDA) if f["salida_producto"].isdigit()]
    litros = dict(
        Producto.objects.filter(pk__in=[f["salida_producto"] for f in filas]).values_list(
            "id", "contenido_litros"
        )
    )
    return tuple(
        dom.Salida(
            int(f["salida_producto"]),
            _decimal(f["salida_cantidad"], "La cantidad", "salidas", Decimal("0")),
            _decimal(f["salida_factor"], "El factor de reparto", "salidas")
            or dom.factor_sugerido(litros.get(int(f["salida_producto"]))),
        )
        for f in filas
    )


def _datos(post, con_componentes: bool) -> uc.DatosOp:
    componentes = None
    if con_componentes:
        componentes = tuple(
            dom.Componente(
                int(f["componente"]),
                _decimal(f["por_consumir"], "La cantidad", "componentes", Decimal("0")),
                _decimal(f["costo"], "El costo del servicio", "componentes"),
                _id(f["para"]),
            )
            for f in _filas(post)
            if f["componente"].isdigit()
        )
    return uc.DatosOp(
        _salidas(post),
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
    filas = OrdenProduccion.objects.select_related("responsable").prefetch_related(
        "salidas__producto__unidad"
    )
    filas = filas.order_by("-numero")
    if filtro["estado"]:
        filas = filas.filter(estado=filtro["estado"])
    if filtro["producto"].isdigit():
        filas = filas.filter(salidas__producto_id=filtro["producto"]).distinct()
    for campo, condicion in (
        ("desde", "fecha_programada__gte"),
        ("hasta", "fecha_programada__lte"),
    ):
        try:
            filas = filas.filter(**{condicion: date.fromisoformat(filtro[campo])})
        except ValueError:  # vacía o mal escrita: no filtra
            pass
    if q := filtro["q"].upper():
        busca = Q(comentario__icontains=q) | Q(salidas__lote_codigo__icontains=q)
        if (n := q.removeprefix("OP-")).isdigit():
            busca |= Q(numero=int(n))
        filas = filas.filter(busca).distinct()
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
        valores, salidas = request.POST, _filas(request.POST, CAMPOS_SALIDA)
    else:
        salidas = [{}]
        principal = Almacen.objects.filter(activo=True).order_by("id").first()
        almacen = str(principal.id) if principal else ""
        valores = {
            "fecha_programada": timezone.localdate().isoformat(),
            "almacen_origen": almacen,
            "almacen_destino": almacen,
            "responsable": str(request.actor.usuario_id),
            "usar_receta": "on",
        }
    contexto = _opciones() | {
        "valores": valores,
        "salidas_form": salidas or [{}],
        "migas": MIGAS + [("Nueva", None)],
    }
    return render(request, "production/orden.html", contexto)


def _componentes(fila, hoy, con_disponibilidad: bool) -> list[dict]:
    """Componentes con su disponibilidad en el almacén de origen (RF-PRD-39) y los lotes que
    se sugieren para consumir (RF-PRD-41)."""
    filas = []
    componentes = fila.componentes.select_related("producto__unidad", "salida__producto")
    for c in componentes.order_by("id"):
        x = {"c": c, "servicio": c.producto.tipo == dom.SERVICIO}
        if con_disponibilidad and not x["servicio"]:
            orden = inventario().existencias_en_orden(c.producto_id, fila.almacen_origen_id, hoy)
            x["disponible"] = sum((q for _, q in orden), Decimal("0")) >= c.por_consumir
            x["lotes"] = orden
            x["previstos"] = _previstos(orden, c.por_consumir)
        if c.consumido is not None:
            x["merma"] = dom.merma(c.por_consumir, c.consumido)
        x["clave"] = f"{c.producto_id}_{c.salida.producto_id if c.salida_id else 'c'}"
        filas.append(x)
    return filas


def _finalizacion(post, fila) -> uc.Finalizacion:
    consumos = []
    for c in fila.componentes.select_related("salida"):
        salida = c.salida.producto_id if c.salida_id else None
        clave = f"{c.producto_id}_{salida or 'c'}"
        consumido = _decimal(
            post.get(f"consumido_{clave}"), "Lo consumido", "componentes", c.por_consumir
        )
        consumos.append(
            uc.ConsumoReal(c.producto_id, consumido, post.get(f"lotecomp_{clave}") or None, salida)
        )
    producidos = []
    for x in fila.salidas.all():
        vence = post.get(f"vence_{x.producto_id}")
        producidos.append(
            uc.Producido(
                x.producto_id,
                _decimal(
                    post.get(f"producida_{x.producto_id}"),
                    "La cantidad producida",
                    "producida",
                    x.cantidad,
                ),
                post.get(f"lote_{x.producto_id}", "").strip(),
                _fecha(vence, "El vencimiento", "vencimiento") if vence else None,
            )
        )
    return uc.Finalizacion(
        tuple(producidos),
        _fecha(post.get("fecha_fin"), "La fecha de fin", "fecha_fin"),
        tuple(consumos),
        _decimal(
            post.get("costo_indirecto"), "El costo indirecto", "costo_indirecto", Decimal("0")
        ),
        post.get("motivo_perdida", ""),
    )


def _salidas_de(fila, componentes, abierta: bool) -> list[dict]:
    """Salidas con su rendimiento y el lote sugerido: el del único lote que consumen sus
    componentes asignados, o los comunes si no tiene (RF-PRD-46, 52)."""
    repo, filas = OrdenesOrm(), []
    for x in fila.salidas.select_related("producto__unidad").order_by("id"):
        d = {"s": x}
        if x.producida is not None:
            d["rendimiento"] = dom.rendimiento(x.cantidad, x.producida)
        if abierta:
            propios = {
                y["c"].producto_id: y.get("previstos", set())
                for y in componentes
                if y["c"].salida_id == x.id
            } or {
                y["c"].producto_id: y.get("previstos", set())
                for y in componentes
                if not y["c"].salida_id
            }
            d["sugerido"] = dom.sugerir_lote(
                propios, x.producto.sku, repo.correlativo_lote(x.producto_id)
            )
        filas.append(d)
    return filas


@requiere(VER)
def orden(request, op_id):
    """Ficha: edición mientras esté Creada o En proceso, con la barra de estados; Finalizada o
    Anulada, solo lectura con la pestaña Costos y sus movimientos (RF-PRD-34, 36 a 46)."""
    relacionados = ("almacen_origen", "almacen_destino", "responsable")
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
            "receta": lambda: _guardar_recetas(actor, _datos(p, True)),
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
    salidas = _salidas_de(fila, componentes, abierta)
    if request.method == "POST" and editable:
        valores, filas = request.POST, _filas(request.POST)
        salidas_form = _filas(request.POST, CAMPOS_SALIDA)
    else:
        salidas_form = [
            {
                "salida_producto": str(d["s"].producto_id),
                "salida_cantidad": d["s"].cantidad.normalize(),
                "salida_factor": d["s"].factor.normalize(),
            }
            for d in salidas
        ]
        valores = {
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
                "para": str(x["c"].salida.producto_id) if x["c"].salida_id else "",
                "x": x,
            }
            for x in componentes
        ]
    ve_costos = actor.puede(REPORTE) and actor.puede(COSTOS)
    contexto = _opciones() | {
        "op": fila,
        "titulo": ", ".join(d["s"].producto.nombre for d in salidas),
        "salidas": salidas,
        "salidas_form": salidas_form or [{}],
        "ids_salida": {d["s"].producto_id for d in salidas},
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
        "accion_fallida": request.POST.get("accion", "guardar") if request.method == "POST" else "",
        "hoy": hoy.isoformat(),
        "movimientos": Movimiento.objects.filter(ref_tipo="OP", ref_id=op_id)
        .select_related("producto", "almacen", "lote")
        .order_by("id"),
        "migas": MIGAS + [(numero_op(fila.numero), None)],
    }
    return render(request, "production/orden.html", contexto)


def _guardar_recetas(actor, datos):
    """RF-PRD-38 y 50: los componentes asignados a cada salida pasan a ser su receta, por
    unidad producida."""
    guardar = caso_de_catalogo(uc_productos.GuardarReceta)
    for x in datos.salidas:
        propios = [c for c in datos.componentes if c.salida == x.producto_id]
        guardar.ejecutar(actor, x.producto_id, dom.receta_desde_op(propios, x.cantidad))
