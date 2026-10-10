from datetime import date

from django.db import migrations


def cargar(apps, schema_editor):
    """IGV vigente en Perú (16 % IGV + 2 % IPM) desde el 2011-03-01."""
    Parametro = apps.get_model("tenancy", "ParametroVigencia")
    Parametro.objects.get_or_create(
        empresa=None, clave="igv_pct", vigente_desde=date(2011, 3, 1), defaults={"valor": 18}
    )


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0003_email_unico")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
