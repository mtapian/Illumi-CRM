"""URLs de prueba: las de la app + una consulta mínima de la API (spec 0001d, T9).

Las consultas reales (stock, pedidos, ventas, productos, resultados) llegan con sus specs.
"""

from django.urls import path
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from config.urls import urlpatterns as urls_app
from tenancy.infrastructure.models import Rol
from tenancy.interfaces.api import VistaApi


class RolesApi(VistaApi):
    permiso = "catalogo.producto.ver"

    def get(self, request):
        paginador = PageNumberPagination()
        filas = paginador.paginate_queryset(Rol.objects.order_by("id"), request, view=self)
        datos = [{"id": r.id, "nombre": r.nombre, "empresa_id": r.empresa_id} for r in filas]
        return paginador.get_paginated_response(datos)


class SinPermisoApi(VistaApi):
    permiso = "finanzas.resultados.ver"

    def get(self, request):
        return Response({"ok": True})


urlpatterns = [
    *urls_app,
    path("api/prueba/", RolesApi.as_view()),
    path("api/prueba-sin-permiso/", SinPermisoApi.as_view()),
]
