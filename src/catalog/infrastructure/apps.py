from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "catalog.infrastructure"
    label = "catalog"
    verbose_name = "Catálogo"

    def ready(self):
        from catalog.infrastructure.contenedor import sembrar_impuestos, sembrar_unidades
        from tenancy.application.sembradores import sembradores

        sembradores.registrar(sembrar_unidades)
        sembradores.registrar(sembrar_impuestos)
