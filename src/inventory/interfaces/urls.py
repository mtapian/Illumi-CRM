from django.urls import path

from inventory.application.ajustes import REGISTRAR
from inventory.application.almacenes import GESTIONAR
from inventory.interfaces import views
from shared.interfaces.avisos import avisos
from shared.interfaces.menu import menu

urlpatterns = [
    path("inventario/almacenes/", views.almacenes, name="almacenes"),
    path("inventario/ajustes/", views.ajustes, name="ajustes"),
    path("inventario/ajustes/<int:ajuste_id>/", views.ajuste, name="ajuste"),
    path("inventario/stock/", views.stock, name="stock"),
    path("inventario/kardex/", views.kardex, name="kardex"),
    path("inventario/configuracion/", views.configuracion, name="configuracion_inventario"),
]

menu.agregar(
    "Inventario", "Almacenes", "/inventario/almacenes/", 200, permiso=GESTIONAR, icono="almacenes"
)
menu.agregar(
    "Inventario", "Ajustes de stock", "/inventario/ajustes/", 210, permiso=REGISTRAR, icono="cubo"
)
for etiqueta, url, orden, permiso in (
    ("Stock", "/inventario/stock/", 190, views.STOCK),
    ("Kardex", "/inventario/kardex/", 195, views.KARDEX),
    ("Configuración", "/inventario/configuracion/", 220, GESTIONAR),
):
    menu.agregar("Inventario", etiqueta, url, orden, permiso=permiso, icono="cubo")
avisos.agregar("stock_bajo", "Stock bajo", views.aviso_stock_bajo, permiso=views.STOCK, orden=10)
avisos.agregar("por_vencer", "Por vencer", views.aviso_por_vencer, permiso=views.STOCK, orden=20)
