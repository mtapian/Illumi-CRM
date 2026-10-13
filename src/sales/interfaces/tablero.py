"""Tarjetas y paneles del inicio que aporta ventas (spec 0008c, RF-FIN-14, 18 a 23)."""

from django.template.loader import render_to_string
from django.utils import timezone

from sales.application import clientes as uc
from sales.application import cobranzas as ucob
from sales.domain.pedido import numero_pedido
from sales.infrastructure import reportes
from sales.infrastructure.models import Cliente
from shared.interfaces import graficos
from shared.interfaces.graficos import soles
from shared.interfaces.tablero import paneles, tarjetas

VENTAS = "ventas.venta.ver"
MESES = (
    "ene.",
    "feb.",
    "mar.",
    "abr.",
    "may.",
    "jun.",
    "jul.",
    "ago.",
    "set.",
    "oct.",
    "nov.",
    "dic.",
)
ESTADOS = {"FACTURADO": "Facturado", "ENTREGADO": "Entregado"}


def _mes(hoy):
    return hoy.replace(day=1), hoy


tarjetas.agregar(
    "ventas_hoy",
    "Ventas de hoy",
    lambda r: soles(reportes.ventas_entre(timezone.localdate(), timezone.localdate())),
    permiso=VENTAS,
    orden=10,
    color="celeste",
    icono="ojo",
)
tarjetas.agregar(
    "ventas_mes",
    "Ventas del mes",
    lambda r: soles(reportes.ventas_entre(*_mes(timezone.localdate()))),
    permiso=VENTAS,
    orden=20,
    color="naranja",
    icono="carrito",
)
tarjetas.agregar(
    "clientes",
    "Clientes activos",
    lambda r: str(Cliente.objects.filter(activo=True).count()),
    permiso=uc.VER,
    orden=40,
    color="verde",
    icono="usuarios",
)


def _ultimos_14_dias(request) -> str:
    puntos = reportes.ventas_por_dia(timezone.localdate(), 14)
    return graficos.linea([(d.strftime("%d/%m"), v) for d, v in puntos], "Ventas de 14 días")


def _por_mes(request) -> str:
    anio = timezone.localdate().year
    puntos = reportes.ventas_por_mes(anio)
    return graficos.linea([(MESES[m - 1], v) for m, v in puntos], f"Ventas por mes ({anio})")


def _cobrado(request) -> str:
    return graficos.dona(reportes.cobrado_por_metodo(*_mes(timezone.localdate())))


def _por_categoria(request) -> str:
    return graficos.barras(reportes.ventas_por_categoria(*_mes(timezone.localdate())))


def _mas_vendidos(request) -> str:
    filas = reportes.mas_vendidos(*_mes(timezone.localdate()))
    return render_to_string("sales/_mas_vendidos.html", {"filas": filas})


def _ultimas(request) -> str:
    ventas = reportes.ultimas_ventas(6)
    for p in ventas:
        p.numero_texto, p.estado_texto = numero_pedido(p.numero), ESTADOS.get(p.estado, p.estado)
    return render_to_string("sales/_ultimas_ventas.html", {"ventas": ventas})


for clave, titulo, funcion, permiso, orden in (
    ("ventas_14", "Ventas de los últimos 14 días", _ultimos_14_dias, VENTAS, 10),
    ("ventas_mes", "Ventas por mes", _por_mes, VENTAS, 20),
    ("cobrado", "Cobrado por método de pago", _cobrado, ucob.VER, 30),
    ("categorias", "Ventas por categoría", _por_categoria, VENTAS, 40),
    ("mas_vendidos", "Productos más vendidos", _mas_vendidos, VENTAS, 50),
    ("ultimas", "Últimas ventas", _ultimas, VENTAS, 60),
):
    paneles.agregar(clave, titulo, funcion, permiso=permiso, orden=orden)
