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
avisos.agregar(  # RF-INV-14: el detalle muestra stock y mínimo
    "stock_bajo",
    views.contar_stock_bajo,
    ("producto con stock bajo o agotado", "productos con stock bajo o agotado"),
    permiso=views.STOCK,
    orden=10,
    detalle=views.aviso_stock_bajo,
)
avisos.agregar(  # RF-INV-15 y 16: el detalle muestra los días que quedan
    "por_vencer",
    views.contar_por_vencer,
    ("lote por vencer o vencido", "lotes por vencer o vencidos"),
    permiso=views.STOCK,
    orden=20,
    detalle=views.aviso_por_vencer,
)
