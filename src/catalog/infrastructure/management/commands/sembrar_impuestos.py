from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.infrastructure.contenedor import sembrar_impuestos
from catalog.infrastructure.models import Impuesto
from tenancy.infrastructure.models import Empresa


class Command(BaseCommand):
    help = "Siembra los seis impuestos iniciales en las empresas que aún no tienen (RF-CAT-52)."

    # ponytail: puente hasta la conversión de T6 (RF-CAT-60), que copia el historial del IGV.
    def handle(self, *args, **options):
        con = set(Impuesto.all_tenants.values_list("empresa_id", flat=True).distinct())
        hoy = timezone.localdate()
        for empresa in Empresa.objects.exclude(pk__in=con):
            with transaction.atomic():
                sembrar_impuestos(empresa.id, None, hoy)
            self.stdout.write(f"Impuestos sembrados: {empresa.razon_social}")
