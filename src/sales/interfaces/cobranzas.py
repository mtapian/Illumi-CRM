"""Pantallas de cobranzas, pagos y métodos de pago (plan 0006b §5; RF-VEN-53 a 60)."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from sales.application import cobranzas as uc
from sales.domain import cobranza as dom
from sales.domain.errores import CobranzaInvalida
from sales.domain.facturacion import Cuota
from sales.domain.pedido import numero_pedido
from sales.infrastructure.contenedor import caso_de_cobranza, metodos_activos
from sales.infrastructure.models import Cliente, Cobranza, MetodoPago
from shared.interfaces import listados
from tenancy.interfaces.acceso import requiere
from tenancy.interfaces.views.accesos import _intentar

ESTADOS = [(dom.PENDIENTE, "Pendiente"), (dom.PARCIAL, "Parcial"), (dom.PAGADA, "Pagada")]
FORMAS = {"CONTADO": "Contado", "CREDITO": "Crédito"}
FILTROS = ("estado", "cliente", "desde", "hasta", "q", "vencidas")
MIGAS = [("Inicio", "/"), ("Ventas", None)]


def _fecha(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None


def _preparar(c, hoy):
    """Código, pedido, saldo, monto vencido y próximo vencimiento de una cobranza."""
    cuotas = tuple(Cuota(q.monto, q.vencimiento) for q in c.cuotas.all())
    c.codigo = dom.numero_cobranza(c.numero)
    c.pedido_texto = numero_pedido(c.pedido.numero)
    c.forma_texto = FORMAS.get(c.pedido.forma_pago, "")
    c.saldo = c.total - c.pagado
    c.vencido = dom.monto_vencido(cuotas, c.pagado, hoy) if c.estado in dom.ABIERTAS else 0
    c.proximo = dom.proximo_vencimiento(cuotas, c.pagado)
    c.es_vencida = dom.vencida(c.estado, cuotas, c.pagado, hoy)
    return c


def _vencidas(filas, hoy):
    """RF-VEN-53 y 62: abiertas con cuotas vencidas − pagado > 0, en la base."""
    return (
        filas.filter(estado__in=dom.ABIERTAS)
        .annotate(vencido_cuotas=Sum("cuotas__monto", filter=Q(cuotas__vencimiento__lt=hoy)))
        .filter(vencido_cuotas__gt=F("pagado"))
    )


def aviso_vencidas(request):
    """RF-VEN-62: aviso del inicio con las cobranzas vencidas."""
    n = _vencidas(Cobranza.objects.all(), timezone.localdate()).count()
    return render_to_string("sales/_aviso_vencidas.html", {"n": n})


@requiere(uc.VER)
def cobranzas(request):
    """RF-VEN-53: grilla estándar con el indicador Vencida y sus filtros."""
    filtro = {k: request.GET.get(k, "").strip() for k in FILTROS}
    hoy = timezone.localdate()
    filas = Cobranza.objects.select_related("pedido", "cliente").prefetch_related("cuotas")
    filas = filas.order_by("-numero")
    if filtro["estado"]:
        filas = filas.filter(estado=filtro["estado"])
    if filtro["cliente"].isdigit():
        filas = filas.filter(cliente_id=filtro["cliente"])
    if desde := _fecha(filtro["desde"]):
        filas = filas.filter(cuotas__vencimiento__gte=desde)
    if hasta := _fecha(filtro["hasta"]):
        filas = filas.filter(cuotas__vencimiento__lte=hasta)
    if q := filtro["q"].upper():
        n = q.removeprefix("COB-").removeprefix("P-")
        numero = Q(numero=int(n)) | Q(pedido__numero=int(n)) if n.isdigit() else Q(pk__in=[])
        filas = filas.filter(numero | Q(cliente__nombre__icontains=filtro["q"]))
    if filtro["vencidas"]:
        filas = _vencidas(filas, hoy)
    filas = filas.distinct()
    pagina = listados.paginar(request, filas)
    for c in pagina:
        _preparar(c, hoy)
        c.estado_texto = dict(ESTADOS)[c.estado]
    clientes = Cliente.objects.filter(cobranzas__isnull=False).distinct().order_by("nombre")
    campos = {
        "estado": ("Estado", dict(ESTADOS)),
        "cliente": ("Cliente", {str(c.id): c.nombre for c in clientes}),
        "desde": ("Vence desde", None),
        "hasta": ("Vence hasta", None),
        "q": ("Buscar", None),
        "vencidas": ("Solo vencidas", {"1": "Sí"}),
    }
    contexto = {
        "pagina": pagina,
        "consulta": listados.consulta(request),
        "aplicados": listados.aplicados(request, campos),
        "filtro": filtro,
        "estados": ESTADOS,
        "clientes": clientes,
        "migas": MIGAS[:1] + [("Cobranzas", None)],
    }
    return render(request, "sales/cobranzas.html", contexto)


def _monto(texto):
    try:
        return Decimal(texto or "0")
    except InvalidOperation:
        raise CobranzaInvalida("El monto no es un número válido", "monto") from None


@requiere(uc.VER)
def cobranza(request, cobranza_id):
    """RF-VEN-54 a 57 y 60: ficha con su pedido, cuotas y pagos; registrar y anular pagos."""
    c = get_object_or_404(
        Cobranza.objects.select_related("pedido", "cliente"), pk=cobranza_id
    )  # art. 3.1: el manager filtra por empresa
    hoy, actor = timezone.localdate(), request.actor
    if request.method == "POST":
        p = request.POST
        acciones = {
            "pagar": lambda: caso_de_cobranza(uc.RegistrarPago).ejecutar(
                actor,
                cobranza_id,
                uc.DatosPago(
                    int(p.get("metodo") or 0),
                    _monto(p.get("monto")),
                    _fecha(p.get("fecha")) or hoy,
                    p.get("referencia", ""),
                ),
                hoy,
            ),
            "anular": lambda: caso_de_cobranza(uc.AnularPago).ejecutar(
                actor, int(p.get("pago") or 0), p.get("motivo", "")
            ),
        }
        accion = p.get("accion", "pagar")
        if _intentar(request, acciones.get(accion, acciones["pagar"])):
            messages.success(request, "Pago anulado." if accion == "anular" else "Pago registrado.")
            return redirect("cobranza", cobranza_id=cobranza_id)
    _preparar(c, hoy)
    c.estado_texto = dict(ESTADOS)[c.estado]
    contexto = {
        "cobranza": c,
        "estado_texto": dict(ESTADOS)[c.estado],
        "cuotas": c.cuotas.order_by("numero"),
        "pagos": c.pagos.select_related("metodo", "registrado_por", "anulado_por").order_by("id"),
        "metodos": metodos_activos(),
        "gestiona": actor.puede(uc.GESTIONAR),
        "anula": actor.puede(uc.ANULAR),
        "hoy": hoy,
        "accion_fallida": request.POST.get("accion", "pagar") if request.method == "POST" else "",
        "migas": MIGAS[:1] + [("Cobranzas", "/ventas/cobranzas/"), (c.codigo, None)],
    }
    return render(request, "sales/cobranza.html", contexto)


@requiere(uc.VER)
def metodos_pago(request):
    """RF-VEN-58 y 59: listado de maestro; crear, renombrar, activar o desactivar; sin
    eliminar."""
    if request.method == "POST":
        p, actor = request.POST, request.actor
        id_ = int(p["id"]) if p.get("id", "").isdigit() else None
        acciones = {
            "guardar": lambda: caso_de_cobranza(uc.GuardarMetodoPago).ejecutar(
                actor, id_, p.get("nombre", "")
            ),
            "activar": lambda: caso_de_cobranza(uc.CambiarEstadoMetodoPago).ejecutar(
                actor, id_, True
            ),
            "desactivar": lambda: caso_de_cobranza(uc.CambiarEstadoMetodoPago).ejecutar(
                actor, id_, False
            ),
        }
        if _intentar(request, acciones.get(p.get("accion"), acciones["guardar"])):
            messages.success(request, "Cambio guardado.")
            return redirect(request.path)
    q = request.GET.get("q", "").strip()
    filas = MetodoPago.objects.annotate(pagos_n=Count("pagos")).order_by("nombre")
    if q:
        filas = filas.filter(nombre__icontains=q)
    editar = request.GET.get("editar", "")
    contexto = {
        "pagina": listados.paginar(request, filas),
        "consulta": listados.consulta(request),
        "q": q,
        "editando": get_object_or_404(MetodoPago, pk=editar) if editar.isdigit() else None,
        "nuevo": "nuevo" in request.GET or request.method == "POST",
        "gestiona": request.actor.puede(uc.METODOS),
        "migas": MIGAS[:1] + [("Métodos de pago", None)],
    }
    return render(request, "sales/metodos_pago.html", contexto)
