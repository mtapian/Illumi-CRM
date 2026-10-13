from django.urls import path

from production.interfaces import views
from shared.interfaces.menu import menu

urlpatterns = [
    path("produccion/", views.ordenes, name="ordenes"),
    path("produccion/nueva/", views.nueva_op, name="nueva_op"),
    path("produccion/<int:op_id>/", views.orden, name="orden"),
]

menu.agregar(
    "Producción",
    "Órdenes de producción",
    "/produccion/",
    250,
    permiso=views.VER,
    icono="produccion",
)
