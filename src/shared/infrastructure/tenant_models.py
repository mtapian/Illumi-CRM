"""Base de los modelos de negocio: siempre filtrados por la empresa actual (plan 0000 §4)."""

from django.db import models

from shared.domain.tenant import empresa_actual


class TenantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(empresa_id=empresa_actual())


class TenantModel(models.Model):
    empresa = models.ForeignKey("tenancy.Empresa", on_delete=models.PROTECT, related_name="+")

    all_tenants = models.Manager()  # solo para rutas /plataforma/* del super admin
    objects = TenantManager()

    class Meta:
        abstract = True
        default_manager_name = "objects"
        base_manager_name = "all_tenants"

    def save(self, *args, **kwargs):
        if self.empresa_id is None:
            self.empresa_id = empresa_actual()
        super().save(*args, **kwargs)
