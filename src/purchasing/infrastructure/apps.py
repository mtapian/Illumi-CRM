from django.apps import AppConfig


class PurchasingConfig(AppConfig):
    name = "purchasing.infrastructure"
    label = "purchasing"
    verbose_name = "Compras"

    def ready(self):
        from purchasing.application.puertos import puertos
        from purchasing.infrastructure.repositorios import ComprasOrm

        puertos.compras = ComprasOrm()  # RF-COM-24: un proveedor con compras no se elimina
