"""Pantallas de clientes y pedidos (plan 0006a §5)."""

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.infrastructure.contenedor import inventario
from sales.application import clientes as uc
from sales.application import pedidos as up
from sales.domain import pedido as dom
from sales.domain.cliente import DatosCliente
from sales.domain.errores import PedidoInvalido
from sales.infrastructure.contenedor import buscar_clientes, caso_de_cliente, caso_de_pedido
from sales.infrastructure.models import Cliente, Pedido
from shared.domain.errores import DomainError
from shared.interfaces import listados
from tenancy.infrastructure.contenedor import tenancy_service
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

CAMPOS_CLIENTE = ("nombre", "tipo_doc", "num_doc", "telefono", "email", "comentarios")
CAMPOS_CLIENTE += ("direccion", "contacto", "canal")
ESTADOS = [
    (dom.CREADO, "Creado"),
    (dom.APROBADO, "Aprobado"),
    (dom.FACTURADO, "Facturado"),
    (dom.ENTREGADO, "Entregado"),
    (dom.CANCELADO, "Cancelado"),
]
CAMPOS_LINEA = ("producto", "cantidad", "precio")
FILTROS = ("estado", "cliente", "desde", "hasta", "q", "atrasados", "quiebre", "vista")
MIGAS = [("Inicio", "/"), ("Ventas", None)]


def _id(texto):
    return int(texto) if texto and str(texto).isdigit() else None


def _tipos(actual=""):
    """Tipos activos del maestro; el del cliente aunque esté inactivo (lo conserva)."""
    tipos = tenancy_service().tipos_documento()
    if actual and actual not in {t.abreviatura for t in tipos}:
        tipos.append(tenancy_service().reglas_documento(actual))
    return [t for t in tipos if t]


def _datos_cliente(post) -> DatosCliente:
    return DatosCliente(
        **{c: post.get(c, "") for c in CAMPOS_CLIENTE},
        activo=post.get("activo", "on") == "on",
    )


# --- Clientes (UC-VEN-01) ---


@requiere(uc.VER)
def clientes(request):
    """Grilla estándar (RF-VEN-43); `?nuevo=1` y `?editar=<id>` abren el formulario; la
    ficha muestra sus pedidos (RF-VEN-04). Sin eliminar (RF-VEN-05)."""
    if request.method == "POST":
        p, actor, id_ = request.POST, request.actor, _id(request.POST.get("id"))
        acciones = {
            "guardar": lambda: caso_de_cliente(uc.GuardarCliente).ejecutar(
                actor, id_, _datos_cliente(p)
            ),
            "activar": lambda: caso_de_cliente(uc.CambiarEstadoCliente).ejecutar(actor, id_, True),
            "desactivar": lambda: caso_de_cliente(uc.CambiarEstadoCliente).ejecutar(
                actor, id_, False
            ),
        }
        if _intentar(request, acciones.get(p.get("accion"), acciones["guardar"])):
            messages.success(request, "Cambio guardado.")
            return redirect(request.path)
    filtro = {k: request.GET.get(k, "").strip() for k in ("q", "canal", "estado")}
    filas = Cliente.objects.order_by("-es_generico", "nombre")
    if q := filtro["q"]:
        filas = filas.filter(Q(nombre__icontains=q) | Q(num_doc__icontains=q))
    if filtro["canal"]:
        filas = filas.filter(canal=filtro["canal"])
    if filtro["estado"] in ("activo", "inactivo"):
        filas = filas.filter(activo=filtro["estado"] == "activo")
    editar = request.GET.get("editar", "")
    fallo = request.method == "POST" and request.POST.get("accion", "guardar") == "guardar"
    if fallo and request.POST.get("id", "").isdigit():
        editar = request.POST["id"]
    editando = get_object_or_404(Cliente, pk=editar) if editar.isdigit() else None  # art. 3.1
    valores = defaultdict(str, request.POST.dict() if request.method == "POST" else {})
    if editando and request.method != "POST":
        valores |= {c: getattr(editando, c) for c in CAMPOS_CLIENTE}
        valores["activo"] = "on" if editando.activo else ""
    nuevo = "nuevo" in request.GET or (fallo and not editando)
    migas = MIGAS[:1] + [("Clientes", None)]
    if nuevo or editando:
        migas = MIGAS[:1] + [("Clientes", request.path), ("Editar" if editando else "Nuevo", None)]
    contexto = {
        "pagina": listados.paginar(request, filas),
        "consulta": listados.consulta(request),
        "filtro": filtro,
        "nuevo": nuevo,
        "editando": editando,
        "valores": valores,
        "tipos": _tipos(valores.get("tipo_doc", "")),
        "pedidos": editando.pedidos.order_by("-numero")[:20] if editando else [],
        "estados": dict(ESTADOS),
        "gestiona": request.actor.puede(uc.GESTIONAR),
        "migas": migas,
    }
    return render(request, "sales/clientes.html", contexto)


@requiere(up.GESTIONAR)
def buscar(request):
    """RF-VEN-50: hasta 10 clientes activos por nombre o documento, en JSON."""
    filas = buscar_clientes(request.actor.empresa_id, request.GET.get("q", ""))
    datos = [
        {"id": c.id, "nombre": c.nombre, "documento": f"{c.tipo_doc} {c.num_doc}".strip()}
        for c in filas
    ]
    return JsonResponse({"clientes": datos})


@requiere(uc.GESTIONAR)
def cliente_rapido(request):
    """RF-VEN-50: registro al vuelo con los datos mínimos; devuelve el cliente o los errores."""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    try:
        nuevo = caso_de_cliente(uc.GuardarCliente).ejecutar(
            request.actor, None, _datos_cliente(request.POST)
        )
    except DomainError as e:
        return JsonResponse({"errores": {e.campo or "nombre": e.mensaje}}, status=400)
    c = Cliente.objects.get(pk=nuevo)
    return JsonResponse({"id": c.id, "nombre": c.nombre})


# --- Pedidos (UC-VEN-02 a 05) ---


def _decimal(texto, campo):
    try:
        return Decimal(texto or "0")
    except InvalidOperation:
        raise PedidoInvalido(f"{campo} no es un número válido", "lineas") from None


def _fecha(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise PedidoInvalido("La fecha de entrega no es válida", "fecha_entrega") from None


def _filas(post) -> list[dict]:
    columnas = [post.getlist(c) for c in CAMPOS_LINEA]
    return [dict(zip(CAMPOS_LINEA, v, strict=False)) for v in zip(*columnas, strict=False)]


def _datos(post) -> up.DatosPedido:
    lineas = tuple(
        dom.LineaPedido(
            int(f["producto"]),
            _decimal(f["cantidad"], "La cantidad"),
            _decimal(f["precio"], "El precio"),
        )
        for f in _filas(post)
        if f["producto"].isdigit()
    )
    return up.DatosPedido(
        _id(post.get("cliente")),
        _fecha(post.get("fecha_entrega")),
        post.get("comentario", ""),
        lineas,
    )


def disponibilidad(pedidos, hoy) -> dict[int, dict]:
    """RF-VEN-45, 46: por pedido abierto, el disponible y el faltante de cada línea (una sola
    consulta de stock) y sus indicadores. ponytail: al vuelo, sin resumen guardado."""
    pedidos = list(pedidos)
    abiertos = [p for p in pedidos if p.estado in (dom.CREADO, dom.APROBADO)]
    lineas = {
        p.id: list(p.lineas.select_related("producto__unidad").order_by("id")) for p in abiertos
    }
    ids = [x.producto_id for filas in lineas.values() for x in filas]
    disponibles = inventario().disponibles(ids, hoy)
    resultado = {}
    for p in pedidos:
        filas = []
        for x in lineas.get(p.id, []):
            servicio = x.producto.tipo == "SERVICIO"
            disponible = None if servicio else disponibles[x.producto_id]
            filas.append(
                {
                    "linea": x,
                    "disponible": disponible,
                    "faltante": dom.faltante(x.cantidad, disponible or 0, servicio),
                }
            )
        marcas = dom.indicadores(p.estado, p.fecha_entrega, [f["faltante"] for f in filas], hoy)
        resultado[p.id] = {"lineas": filas, "indicadores": marcas}
    return resultado


@requiere(up.VER)
def pedidos(request):
    """Lista o Kanban con los mismos filtros e indicadores (RF-VEN-15, 46)."""
    filtro = {k: request.GET.get(k, "").strip() for k in FILTROS}
    vista = "kanban" if filtro["vista"] == "kanban" else "lista"
    filas = Pedido.objects.select_related("cliente").order_by("fecha_entrega", "numero")
    if filtro["estado"]:
        filas = filas.filter(estado=filtro["estado"])
    elif vista == "kanban":
        filas = filas.exclude(estado=dom.CANCELADO)  # Cancelado solo si se filtra por él
    if filtro["cliente"].isdigit():
        filas = filas.filter(cliente_id=filtro["cliente"])
    for campo, condicion in (("desde", "fecha_entrega__gte"), ("hasta", "fecha_entrega__lte")):
        try:
            filas = filas.filter(**{condicion: date.fromisoformat(filtro[campo])})
        except ValueError:
            pass
    if (n := filtro["q"].upper().removeprefix("P-")).isdigit():
        filas = filas.filter(numero=int(n))
    hoy = timezone.localdate()
    info = disponibilidad(filas, hoy)
    elegidos = [
        p
        for p in filas
        if (not filtro["atrasados"] or "Atrasado" in info[p.id]["indicadores"])
        and (not filtro["quiebre"] or "Quiebre de stock" in info[p.id]["indicadores"])
    ]
    for p in elegidos:
        p.indicadores = info[p.id]["indicadores"]
        p.numero_texto = dom.numero_pedido(p.numero)
    columnas = [
        (v, n, [p for p in elegidos if p.estado == v])
        for v, n in ESTADOS
        if v != dom.CANCELADO or filtro["estado"] == dom.CANCELADO
    ]
    clientes_filtro = Cliente.objects.order_by("nombre")
    campos = {
        "estado": ("Estado", dict(ESTADOS)),
        "cliente": ("Cliente", {str(c.id): c.nombre for c in clientes_filtro}),
        "desde": ("Entrega desde", None),
        "hasta": ("Entrega hasta", None),
        "q": ("N.°", None),
        "atrasados": ("Solo atrasados", {"1": "Sí"}),
        "quiebre": ("Solo con quiebre de stock", {"1": "Sí"}),
    }
    contexto = {
        "vista": vista,
        "pagina": listados.paginar(request, elegidos),
        "columnas": columnas,
        "consulta": listados.consulta(request),
        "aplicados": listados.aplicados(request, campos),
        "filtro": filtro,
        "estados": ESTADOS,
        "clientes": clientes_filtro,
        "puede_crear": request.actor.puede(up.GESTIONAR),
        "migas": MIGAS,
    }
    return render(request, "sales/pedidos.html", contexto)


def _formulario(request, pedido=None) -> dict:
    if request.method == "POST":
        valores, filas = request.POST, _filas(request.POST)
        cliente = Cliente.objects.filter(pk=_id(request.POST.get("cliente"))).first()
    elif pedido:
        valores = {
            "cliente": str(pedido.cliente_id),
            "fecha_entrega": pedido.fecha_entrega.isoformat(),
            "comentario": pedido.comentario,
        }
        filas = [
            {"producto": str(x.producto_id), "cantidad": x.cantidad.normalize(), "precio": x.precio}
            for x in pedido.lineas.order_by("id")
        ]
        cliente = pedido.cliente
    else:
        valores, filas, cliente = {"fecha_entrega": timezone.localdate().isoformat()}, [], None
    productos = Producto.objects.filter(activo=True, se_vende=True).select_related("unidad")
    return {
        "valores": valores,
        "filas": filas or [{}],
        "cliente_elegido": cliente,
        "productos": productos.order_by("nombre"),
        "tipos": _tipos(),
        "puede_registrar_cliente": request.actor.puede(uc.GESTIONAR),
    }


@requiere(up.GESTIONAR)
def nuevo_pedido(request):
    """RF-VEN-06: queda Creado, sin efecto en el stock."""
    if request.method == "POST":
        nuevo = {}

        def crear():
            nuevo["id"] = caso_de_pedido(up.CrearPedido).ejecutar(
                request.actor, _datos(request.POST)
            )

        if _intentar(request, crear):
            messages.success(request, "Pedido creado.")
            return redirect("pedido", pedido_id=nuevo["id"])
    contexto = _formulario(request) | {
        "migas": MIGAS[:1] + [("Pedidos", "/ventas/pedidos/"), ("Nuevo", None)]
    }
    return render(request, "sales/pedido.html", contexto)


@requiere(up.VER)
def pedido(request, pedido_id):
    """Ficha con la barra de estados, la disponibilidad por línea y sus acciones (RF-VEN-07,
    08, 11, 37, 45, 48)."""
    fila = get_object_or_404(Pedido.objects.select_related("cliente"), pk=pedido_id)
    hoy, actor = timezone.localdate(), request.actor
    if request.method == "POST":
        p = request.POST
        acciones = {
            "guardar": lambda: caso_de_pedido(up.EditarPedido).ejecutar(
                actor, pedido_id, _datos(p)
            ),
            "aprobar": lambda: (
                caso_de_pedido(up.EditarPedido).ejecutar(actor, pedido_id, _datos(p))
                if fila.estado == dom.CREADO
                else None,
                caso_de_pedido(up.AprobarPedido).ejecutar(actor, pedido_id, hoy),
            ),
            "cancelar": lambda: caso_de_pedido(up.CancelarPedido).ejecutar(
                actor, pedido_id, p.get("motivo", "")
            ),
        }
        accion = p.get("accion", "guardar")
        if _intentar(request, acciones.get(accion, acciones["guardar"])):
            resultado = {"aprobar": "Pedido aprobado.", "cancelar": "Pedido cancelado."}
            messages.success(request, resultado.get(accion, "Cambios guardados."))
            return redirect("pedido", pedido_id=pedido_id)
    gestiona = actor.puede(up.GESTIONAR)
    editable = fila.estado == dom.CREADO and gestiona
    info = disponibilidad([fila], hoy)[fila.id]
    contexto = (_formulario(request, fila) if editable else {}) | {
        "pedido": fila,
        "numero": dom.numero_pedido(fila.numero),
        "estado_texto": dict(ESTADOS)[fila.estado],
        "estados": ESTADOS[:4],
        "editable": editable,
        "fecha_editable": fila.estado == dom.APROBADO and gestiona,
        "lineas_info": info["lineas"],
        "indicadores": info["indicadores"],
        "puede_aprobar": fila.estado == dom.CREADO and gestiona,
        "puede_cancelar": fila.estado in (dom.CREADO, dom.APROBADO) and actor.puede(up.CANCELAR),
        "accion_fallida": request.POST.get("accion", "guardar") if request.method == "POST" else "",
        "migas": MIGAS[:1]
        + [("Pedidos", "/ventas/pedidos/"), (dom.numero_pedido(fila.numero), None)],
    }
    return render(request, "sales/pedido.html", contexto)


def aviso_quiebre(request):
    """RF-VEN-47: alerta con los pedidos Creados o Aprobados con quiebre de stock."""
    abiertos = Pedido.objects.filter(estado__in=(dom.CREADO, dom.APROBADO))
    info = disponibilidad(abiertos, timezone.localdate())
    n = sum("Quiebre de stock" in i["indicadores"] for i in info.values())
    return render_to_string("sales/_aviso_quiebre.html", {"n": n})
