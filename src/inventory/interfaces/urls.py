from django.urls import path

from inventory.application.almacenes import GESTIONAR
from inventory.interfaces import views
from shared.interfaces.menu import menu

urlpatterns = [
    path("inventario/almacenes/", views.almacenes, name="almacenes"),
]

menu.agregar(
    "Inventario", "Almacenes", "/inventario/almacenes/", 200, permiso=GESTIONAR, icono="almacenes"
)
