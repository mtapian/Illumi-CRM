from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import Empresa


class Command(BaseCommand):
    help = (
        "Marca VENCIDA a las empresas cuya prueba o suscripción terminó (cron diario, RF-TEN-18)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--hoy", help="Fecha en hora de Lima (AAAA-MM-DD); por defecto, hoy")

    def handle(self, *args, hoy=None, **options):
        hoy = date.fromisoformat(hoy) if hoy else timezone.localdate()
        # Nunca borra datos (RF-TEN-20): solo cambia el estado.
        vencidas = Empresa.objects.filter(
            estado__in=[Estado.TRIAL, Estado.ACTIVA], fecha_termino__lt=hoy
        ).update(estado=Estado.VENCIDA)
        self.stdout.write(f"Empresas marcadas como vencidas: {vencidas}")
