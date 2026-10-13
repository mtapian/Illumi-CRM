from django.apps import AppConfig


class SalesConfig(AppConfig):
    name = "sales.infrastructure"
    label = "sales"
    verbose_name = "Ventas"

    def ready(self):
        from sales.infrastructure.contenedor import sembrar_cliente_generico
        from tenancy.application.sembradores import sembradores

        sembradores.registrar(sembrar_cliente_generico)  # RF-VEN-03
