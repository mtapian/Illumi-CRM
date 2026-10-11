from django.urls import path

from catalog.interfaces.pestanas import pestanas
from purchasing.application.proveedores import GESTIONAR
from purchasing.interfaces import views
from shared.interfaces.menu import menu

urlpatterns = [
    path("compras/proveedores/", views.proveedores, name="proveedores"),
    path("compras/proveedores/producto/", views.proveedor_producto, name="proveedor_producto"),
]

menu.agregar(
    "Compras", "Proveedores", "/compras/proveedores/", 300, permiso=GESTIONAR, icono="proveedores"
)
pestanas.agregar("compras", "Compras", "se_compra", views.pestana_compras, orden=40)
