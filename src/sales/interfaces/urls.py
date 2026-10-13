from django.urls import path

from sales.application import clientes as uc
from sales.application import cobranzas as ucob
from sales.application import facturacion as uf
from sales.application import pedidos as up
from sales.interfaces import cobranzas, views
from shared.interfaces.avisos import avisos
from shared.interfaces.menu import menu

urlpatterns = [
    path("ventas/clientes/", views.clientes, name="clientes"),
    path("ventas/clientes/buscar/", views.buscar, name="buscar_clientes"),
    path("ventas/clientes/rapido/", views.cliente_rapido, name="cliente_rapido"),
    path("ventas/pedidos/", views.pedidos, name="pedidos"),
    path("ventas/pedidos/nuevo/", views.nuevo_pedido, name="nuevo_pedido"),
    path("ventas/pedidos/<int:pedido_id>/", views.pedido, name="pedido"),
    path("ventas/venta-directa/", views.venta_directa, name="venta_directa"),
    path("ventas/cobranzas/", cobranzas.cobranzas, name="cobranzas"),
    path("ventas/cobranzas/<int:cobranza_id>/", cobranzas.cobranza, name="cobranza"),
    path("ventas/metodos-pago/", cobranzas.metodos_pago, name="metodos_pago"),
]

menu.agregar(
    "Ventas", "Venta directa", "/ventas/venta-directa/", 255, permiso=uf.REGISTRAR, icono="carrito"
)
menu.agregar("Ventas", "Pedidos", "/ventas/pedidos/", 260, permiso=up.VER, icono="cubo")
menu.agregar("Ventas", "Clientes", "/ventas/clientes/", 270, permiso=uc.VER, icono="usuarios")
menu.agregar(
    "Ventas", "Cobranzas", "/ventas/cobranzas/", 275, permiso=ucob.VER, icono="suscripcion"
)
menu.agregar(
    "Ventas", "Métodos de pago", "/ventas/metodos-pago/", 280, permiso=ucob.METODOS, icono="token"
)
avisos.agregar(
    "cobranzas_vencidas", "Cobranzas vencidas", cobranzas.aviso_vencidas, permiso=ucob.VER, orden=35
)
avisos.agregar("quiebre", "Quiebre de stock", views.aviso_quiebre, permiso=up.VER, orden=30)
