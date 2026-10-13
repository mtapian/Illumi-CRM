"""Pantallas de clientes y pedidos (plan 0006a §5)."""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import F, Max, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from catalog.infrastructure.models import Producto
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen
from sales.application import clientes as uc
from sales.application import cobranzas as ucob
from sales.application import facturacion as uf
from sales.application import pedidos as up
from sales.domain import facturacion as fac
from sales.domain import pedido as dom
from sales.domain.cliente import DatosCliente
from sales.domain.cobranza import numero_cobranza
from sales.domain.errores import PedidoInvalido
from sales.infrastructure.contenedor import (
    buscar_clientes,
    caso_de_cliente,
    caso_de_factura,
    caso_de_pedido,
    caso_de_venta_directa,
    metodos_activos,
)
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
COSTOS = "inventario.costo.ver"
FORMAS = {fac.CONTADO: "Contado", fac.CREDITO: "Crédito"}
ESTADOS_COBRANZA = {"PENDIENTE": "Pendiente", "PARCIAL": "Parcial", "PAGADA": "Pagada"}
DIAS_CREDITO = 30  # una cuota por el total a 30 días, editable (RF-VEN-19)


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
        "resumen": _resumen_cliente(editando) if editando else None,
        "estados": dict(ESTADOS),
        "gestiona": request.actor.puede(uc.GESTIONAR),
        "migas": migas,
    }
    return render(request, "sales/clientes.html", contexto)


@requiere(uc.VER)
def buscar(request):
    """RF-VEN-50: hasta 10 clientes activos por nombre o documento, en JSON. Buscar es ver
    clientes: lo usan el pedido y la venta directa (un rol de mostrador no gestiona pedidos)."""
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


def _lineas(post) -> tuple[dom.LineaPedido, ...]:
    return tuple(
        dom.LineaPedido(
            int(f["producto"]),
            _decimal(f["cantidad"], "La cantidad"),
            _decimal(f["precio"], "El precio"),
        )
        for f in _filas(post)
        if f["producto"].isdigit()
    )


def _datos(post) -> up.DatosPedido:
    return up.DatosPedido(
        _id(post.get("cliente")),
        _fecha(post.get("fecha_entrega")),
        post.get("comentario", ""),
        _lineas(post),
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


def _resumen_cliente(cliente) -> dict:
    """RF-VEN-04 (0006b): comprado en 90 días, última compra y saldo por cobrar."""
    desde = timezone.localdate() - timedelta(days=90)
    facturados = cliente.pedidos.filter(fecha_emision__isnull=False)
    return {
        "comprado_90": facturados.filter(fecha_emision__gte=desde).aggregate(t=Sum("total"))["t"]
        or Decimal("0.00"),
        "ultima": facturados.aggregate(u=Max("fecha_emision"))["u"],
        "saldo": cliente.cobranzas.aggregate(s=Sum(F("total") - F("pagado")))["s"]
        or Decimal("0.00"),
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


def _datos_factura(post, hoy) -> uf.DatosFactura:
    """RF-VEN-19 y 20: almacén, forma de pago, cuotas (monto y días) y lote por línea."""
    cuotas = []
    for monto, dias in zip(post.getlist("cuota_monto"), post.getlist("cuota_dias"), strict=False):
        if not (monto or dias):
            continue
        if not dias.strip().lstrip("-").isdigit():
            raise PedidoInvalido("Los días de cada cuota deben ser un número entero", "cuotas")
        cuotas.append(fac.Cuota(_decimal(monto, "El monto"), fac.vencimiento_en(hoy, int(dias))))
    lotes = {
        int(k.removeprefix("lote_")): v
        for k, v in post.items()
        if k.startswith("lote_") and k.removeprefix("lote_").isdigit() and v
    }
    forma = post.get("forma_pago") or fac.CONTADO
    return uf.DatosFactura(_id(post.get("almacen")), forma, tuple(cuotas), lotes)


def _para_facturar(fila, lineas_info, hoy) -> dict:
    """El diálogo "Facturar": comprobante según el cliente, almacenes y lotes con stock."""
    almacenes = list(Almacen.objects.filter(activo=True).order_by("nombre"))
    lotes = {}
    for x in lineas_info:
        if x["disponible"] is None:  # servicio
            continue
        lotes[x["linea"].producto_id] = [
            (a.id, lote, q)
            for a in almacenes
            for lote, q in inventario().existencias_en_orden(x["linea"].producto_id, a.id, hoy)
            if lote
        ]
    return {
        "comprobante": fac.comprobante_para(fila.cliente.tipo_doc),
        "almacenes": almacenes,
        "lotes": lotes,
        "dias_credito": DIAS_CREDITO,
    }


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
            "facturar": lambda: caso_de_factura(uf.FacturarPedido).ejecutar(
                actor, pedido_id, _datos_factura(p, hoy), hoy
            ),
            "entregar": lambda: caso_de_factura(uf.EntregarPedido).ejecutar(actor, pedido_id),
        }
        accion = p.get("accion", "guardar")
        if _intentar(request, acciones.get(accion, acciones["guardar"])):
            resultado = {
                "aprobar": "Pedido aprobado.",
                "cancelar": "Pedido cancelado.",
                "facturar": "Pedido facturado: salió el stock y se generó la cobranza.",
                "entregar": "Entrega confirmada.",
            }
            messages.success(request, resultado.get(accion, "Cambios guardados."))
            return redirect("pedido", pedido_id=pedido_id)
    gestiona = actor.puede(up.GESTIONAR)
    editable = fila.estado == dom.CREADO and gestiona
    info = disponibilidad([fila], hoy)[fila.id]
    registra = actor.puede(uf.REGISTRAR)
    puede_facturar = fila.estado == dom.APROBADO and registra
    facturado = fila.estado in (dom.FACTURADO, dom.ENTREGADO) or fila.fecha_emision is not None
    cobranza = getattr(fila, "cobranza", None) if facturado else None
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
        "puede_facturar": puede_facturar,
        "facturar": _para_facturar(fila, info["lineas"], hoy) if puede_facturar else {},
        "puede_entregar": fila.estado == dom.FACTURADO and registra,
        "facturado": facturado,
        "lineas_facturadas": (
            fila.lineas.select_related("producto__unidad").order_by("id") if facturado else []
        ),
        "forma_texto": FORMAS.get(fila.forma_pago, ""),
        "cobranza": cobranza,
        "cuotas": cobranza.cuotas.order_by("numero") if cobranza else [],
        "cobranza_codigo": numero_cobranza(cobranza.numero) if cobranza else "",
        "cobranza_estado": ESTADOS_COBRANZA.get(cobranza.estado, "") if cobranza else "",
        "cobranza_saldo": cobranza.total - cobranza.pagado if cobranza else None,
        "puede_cobrar": actor.puede(ucob.GESTIONAR),
        "ve_costos": actor.puede(COSTOS),
        "accion_fallida": request.POST.get("accion", "guardar") if request.method == "POST" else "",
        "migas": MIGAS[:1]
        + [("Pedidos", "/ventas/pedidos/"), (dom.numero_pedido(fila.numero), None)],
    }
    return render(request, "sales/pedido.html", contexto)


def _token(texto):
    try:
        return uuid.UUID(texto)
    except (TypeError, ValueError):
        return uuid.uuid4()


def _datos_venta(post) -> uf.DatosVentaDirecta:
    """RF-VEN-18: líneas como en el pedido y pagos (método, monto)."""
    pagos = tuple(
        (int(m), _decimal(monto, "El monto del pago"))
        for m, monto in zip(post.getlist("pago_metodo"), post.getlist("pago_monto"), strict=False)
        if m.isdigit() and monto.strip()
    )
    return uf.DatosVentaDirecta(
        _id(post.get("cliente")),
        _id(post.get("almacen")),
        _lineas(post),
        pagos,
        _token(post.get("token")),
    )


@requiere(uf.REGISTRAR)
def venta_directa(request):
    """RF-VEN-18, 29 y 52: mostrador; crea, factura al contado, cobra y entrega.
    ponytail: sin elegir lotes (sale por la estrategia del producto); se elige en el pedido."""
    if request.method == "POST":
        nuevo = {}

        def vender():
            nuevo["id"] = caso_de_venta_directa().ejecutar(
                request.actor, _datos_venta(request.POST), timezone.localdate()
            )

        if _intentar(request, vender):
            messages.success(request, "Venta registrada: pedido entregado y cobranza pagada.")
            return redirect("pedido", pedido_id=nuevo["id"])
        filas = request.POST.getlist("pago_metodo")
        pagos = [
            {"metodo": m, "monto": monto}
            for m, monto in zip(filas, request.POST.getlist("pago_monto"), strict=False)
        ]
        token = request.POST.get("token")
    else:
        pagos, token = [{}], str(uuid.uuid4())
    contexto = _formulario(request)
    if request.method != "POST":
        contexto["cliente_elegido"] = Cliente.objects.filter(es_generico=True).first()
    contexto |= {
        "almacenes": Almacen.objects.filter(activo=True).order_by("nombre"),
        "metodos": metodos_activos(),
        "pagos": pagos or [{}],
        "token": token,
        "migas": MIGAS[:1] + [("Venta directa", None)],
    }
    return render(request, "sales/venta_directa.html", contexto)


def aviso_quiebre(request):
    """RF-VEN-47: alerta con los pedidos Creados o Aprobados con quiebre de stock."""
    abiertos = Pedido.objects.filter(estado__in=(dom.CREADO, dom.APROBADO))
    info = disponibilidad(abiertos, timezone.localdate())
    n = sum("Quiebre de stock" in i["indicadores"] for i in info.values())
    return render_to_string("sales/_aviso_quiebre.html", {"n": n})
