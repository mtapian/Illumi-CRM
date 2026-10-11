from django.urls import path

from catalog.interfaces.pestanas import pestanas
from purchasing.application.compras import VER
from purchasing.application.proveedores import GESTIONAR
from purchasing.interfaces import views
from shared.interfaces.menu import menu

urlpatterns = [
    path("compras/", views.compras, name="compras"),
    path("compras/nueva/", views.nueva_compra, name="nueva_compra"),
    path("compras/<int:compra_id>/", views.compra, name="compra"),
    path("compras/proveedores/", views.proveedores, name="proveedores"),
    path("compras/proveedores/producto/", views.proveedor_producto, name="proveedor_producto"),
]

menu.agregar("Compras", "Compras", "/compras/", 290, permiso=VER, icono="cubo")
menu.agregar(
    "Compras", "Proveedores", "/compras/proveedores/", 300, permiso=GESTIONAR, icono="proveedores"
)
pestanas.agregar("compras", "Compras", "se_compra", views.pestana_compras, orden=40)
