from django.urls import path

from catalog.interfaces import views
from catalog.interfaces.api import ProductosApi
from shared.interfaces.menu import menu

urlpatterns = [
    path("catalogo/productos/", views.productos, name="productos"),
    path("catalogo/productos/nuevo/", views.producto_nuevo, name="producto_nuevo"),
    path("catalogo/productos/<int:producto_id>/", views.producto, name="producto"),
    path("catalogo/unidades/", views.unidades, name="unidades"),
    path("catalogo/familias/", views.familias, name="familias"),
    path("catalogo/isc/", views.isc, name="isc"),
    path("api/v1/productos/", ProductosApi.as_view(), name="api_productos"),
]

for etiqueta, url, orden, permiso in (
    ("Productos", "/catalogo/productos/", 100, "catalogo.producto.ver"),
    ("Unidades", "/catalogo/unidades/", 110, "catalogo.unidad.gestionar"),
    ("Familias", "/catalogo/familias/", 120, "catalogo.producto.gestionar"),
    ("Categorías de ISC", "/catalogo/isc/", 130, "catalogo.isc.gestionar"),
):
    menu.agregar("Catálogo", etiqueta, url, orden, permiso=permiso)
