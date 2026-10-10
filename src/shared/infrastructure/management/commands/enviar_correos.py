from django.core.management.base import BaseCommand

from shared.infrastructure.correo import enviar_pendientes


class Command(BaseCommand):
    help = "Envía los correos pendientes del outbox (cron cada minuto)."

    def handle(self, *args, **options):
        self.stdout.write(f"Correos enviados: {enviar_pendientes()}")
