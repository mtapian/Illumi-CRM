from datetime import date

from django.db import migrations


def cargar(apps, schema_editor):
    """Umbral de la boleta a un cliente sin identificar: S/ 700.00 (0006b, RF-VEN-25).
    La vigencia exacta queda para el contador (duda abierta de 0006b)."""
    Parametro = apps.get_model("tenancy", "ParametroVigencia")
    Parametro.objects.get_or_create(
        empresa=None,
        clave="umbral_boleta_identificada",
        vigente_desde=date(2011, 3, 1),
        defaults={"valor": 700},
    )


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0010_tipos_documento")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
