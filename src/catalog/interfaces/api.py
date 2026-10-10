"""`GET /api/v1/productos/`: catálogo para integraciones como n8n (RF-TEN-48)."""

from rest_framework.pagination import PageNumberPagination

from catalog.infrastructure.models import Producto
from tenancy.interfaces.api import VistaApi


class ProductosApi(VistaApi):
    permiso = "catalogo.producto.ver"

    def get(self, request):
        paginador = PageNumberPagination()
        filas = Producto.objects.select_related("unidad").order_by("sku")
        pagina = paginador.paginate_queryset(filas, request, view=self)
        return paginador.get_paginated_response(
            [
                {
                    "id": p.id,
                    "sku": p.sku,
                    "nombre": p.nombre,
                    "tipo": p.tipo,
                    "unidad": p.unidad.abreviatura,
                    "precio_venta": str(p.precio_venta) if p.precio_venta else None,
                    "controla_lote": p.controla_lote,
                    "activo": p.activo,
                }
                for p in pagina
            ]
        )
