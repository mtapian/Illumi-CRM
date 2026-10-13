from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("", include("tenancy.interfaces.urls")),
    path("", include("catalog.interfaces.urls")),
    path("", include("purchasing.interfaces.urls")),
    path("", include("inventory.interfaces.urls")),
    path("", include("production.interfaces.urls")),
    path("", include("sales.interfaces.urls")),
]

if settings.SERVIR_MEDIA:
    # Solo los logos (públicos por naturaleza). Los XML/CDR se sirven por vistas con
    # chequeo de empresa, nunca por URL directa (plan 0000 §9).
    urlpatterns += [
        re_path(r"^media/(?P<path>logos/.+)$", serve, {"document_root": settings.MEDIA_ROOT})
    ]
