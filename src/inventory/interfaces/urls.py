from django.urls import path

from inventory.application.ajustes import REGISTRAR
from inventory.application.almacenes import GESTIONAR
from inventory.interfaces import views
from shared.interfaces.menu import menu

urlpatterns = [
    path("inventario/almacenes/", views.almacenes, name="almacenes"),
    path("inventario/ajustes/", views.ajustes, name="ajustes"),
    path("inventario/ajustes/<int:ajuste_id>/", views.ajuste, name="ajuste"),
]

menu.agregar(
    "Inventario", "Almacenes", "/inventario/almacenes/", 200, permiso=GESTIONAR, icono="almacenes"
)
menu.agregar(
    "Inventario", "Ajustes de stock", "/inventario/ajustes/", 210, permiso=REGISTRAR, icono="cubo"
)
