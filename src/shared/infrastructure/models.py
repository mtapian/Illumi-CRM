"""Modelos del shared kernel (plan 0000 §3)."""

from django.db import models

from shared.infrastructure.tenant_models import TenantModel


class Secuencia(TenantModel):
    """Último correlativo por empresa, documento y serie (RN-GEN-06)."""

    documento = models.CharField(max_length=30)
    serie = models.CharField(max_length=10, blank=True)
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "documento", "serie"], name="una_secuencia_por_serie"
            )
        ]

    def __str__(self):
        return f"{self.documento} {self.serie}: {self.ultimo_numero}"


class Correo(models.Model):
    """Outbox de correos (constitución art. 7.4). `empresa` vacía = correo de plataforma."""

    empresa = models.ForeignKey(
        "tenancy.Empresa", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    destinatario = models.EmailField()
    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    estado = models.CharField(
        max_length=10,
        choices=[("PENDIENTE", "Pendiente"), ("ENVIADO", "Enviado")],
        default="PENDIENTE",
    )
    intentos = models.PositiveSmallIntegerField(default=0)
    enviado_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.destinatario}: {self.asunto}"
