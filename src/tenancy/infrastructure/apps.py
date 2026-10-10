from django.apps import AppConfig
from django.db.models.signals import post_migrate


class TenancyConfig(AppConfig):
    name = "tenancy.infrastructure"
    label = "tenancy"
    verbose_name = "Tenancy y accesos"

    def ready(self):
        from tenancy.application.sembradores import sembradores
        from tenancy.infrastructure.catalogo import sincronizar_catalogo
        from tenancy.infrastructure.contenedor import sembrador_roles

        post_migrate.connect(sincronizar_catalogo, sender=self)
        sembradores.registrar(sembrador_roles())
