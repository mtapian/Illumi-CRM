from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = "inventory.infrastructure"
    label = "inventory"
    verbose_name = "Inventario"

    def ready(self):
        from catalog.application.puertos import puertos
        from inventory.infrastructure.contenedor import sembrar_almacen
        from inventory.infrastructure.repositorios import InventarioConsulta
        from tenancy.application.sembradores import sembradores

        sembradores.registrar(sembrar_almacen)
        puertos.inventario = InventarioConsulta()  # el catálogo ve el stock real (RF-CAT-16, 43)
