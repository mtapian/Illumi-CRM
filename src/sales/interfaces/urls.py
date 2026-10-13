from django.urls import path

from sales.application import clientes as uc
from sales.application import pedidos as up
from sales.interfaces import views
from shared.interfaces.avisos import avisos
from shared.interfaces.menu import menu

urlpatterns = [
    path("ventas/clientes/", views.clientes, name="clientes"),
    path("ventas/clientes/buscar/", views.buscar, name="buscar_clientes"),
    path("ventas/clientes/rapido/", views.cliente_rapido, name="cliente_rapido"),
    path("ventas/pedidos/", views.pedidos, name="pedidos"),
    path("ventas/pedidos/nuevo/", views.nuevo_pedido, name="nuevo_pedido"),
    path("ventas/pedidos/<int:pedido_id>/", views.pedido, name="pedido"),
]

menu.agregar("Ventas", "Pedidos", "/ventas/pedidos/", 260, permiso=up.VER, icono="cubo")
menu.agregar("Ventas", "Clientes", "/ventas/clientes/", 270, permiso=uc.VER, icono="usuarios")
avisos.agregar("quiebre", "Quiebre de stock", views.aviso_quiebre, permiso=up.VER, orden=30)
