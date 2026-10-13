from django.apps import AppConfig


class SalesConfig(AppConfig):
    name = "sales.infrastructure"
    label = "sales"
    verbose_name = "Ventas"

    def ready(self):
        from sales.infrastructure.contenedor import sembrar_cliente_generico, sembrar_metodos_pago
        from tenancy.application.sembradores import sembradores

        sembradores.registrar(sembrar_cliente_generico)  # RF-VEN-03
        sembradores.registrar(sembrar_metodos_pago)  # RF-VEN-58
