from django.db import connection

from shared.domain.tenant import empresa_actual


class SecuenciaPostgres:
    """Implementa `SequencePort` con `fn_siguiente_correlativo`."""

    def siguiente(self, documento: str, serie: str = "") -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT fn_siguiente_correlativo(%s, %s, %s)", [empresa_actual(), documento, serie]
            )
            return cursor.fetchone()[0]
