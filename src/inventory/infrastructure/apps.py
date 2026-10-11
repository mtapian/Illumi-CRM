from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = "inventory.infrastructure"
    label = "inventory"
    verbose_name = "Inventario"

    def ready(self):
        from inventory.infrastructure.contenedor import sembrar_almacen
        from tenancy.application.sembradores import sembradores

        sembradores.registrar(sembrar_almacen)
