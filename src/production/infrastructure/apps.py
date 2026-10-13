from django.apps import AppConfig


class ProductionConfig(AppConfig):
    name = "production.infrastructure"
    label = "production"
    verbose_name = "Producción"

    def ready(self):
        from production.domain.op import CREADA, EN_PROCESO
        from production.infrastructure.models import OrdenProduccion
        from tenancy.application.operaciones_en_curso import ContadorOperacionesEnCurso, contadores

        def en_curso(empresa_id: int) -> int:
            filas = OrdenProduccion.all_tenants.filter(empresa_id=empresa_id)
            return filas.filter(estado__in=[CREADA, EN_PROCESO]).count()

        contadores.registrar(  # RF-TEN-32 (0001b): "falso hasta 0005"
            ContadorOperacionesEnCurso(
                "produccion.op",
                en_curso,
                "La empresa tiene {n} OP en curso; quedarán sin poder operarse",
            )
        )
