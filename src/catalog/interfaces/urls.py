from django.urls import path

from catalog.interfaces import views
from catalog.interfaces.api import ProductosApi
from shared.interfaces.menu import menu

urlpatterns = [
    path("catalogo/productos/", views.productos, name="productos"),
    path("catalogo/productos/nuevo/", views.producto_nuevo, name="producto_nuevo"),
    path("catalogo/productos/<int:producto_id>/", views.producto, name="producto"),
    path("catalogo/unidades/", views.unidades, name="unidades"),
    path("catalogo/categorias/", views.categorias, name="categorias"),
    path("catalogo/marcas/", views.marcas, name="marcas"),
    path("api/v1/productos/", ProductosApi.as_view(), name="api_productos"),
]

for etiqueta, url, orden, permiso, icono in (
    ("Productos", "/catalogo/productos/", 100, "catalogo.producto.ver", "productos"),
    ("Unidades de medida", "/catalogo/unidades/", 110, "catalogo.unidad.gestionar", "unidades"),
    ("Categorías", "/catalogo/categorias/", 120, "catalogo.producto.gestionar", "categorias"),
    ("Marcas", "/catalogo/marcas/", 125, "catalogo.producto.gestionar", "marcas"),
):
    menu.agregar("Catálogo", etiqueta, url, orden, permiso=permiso, icono=icono)
