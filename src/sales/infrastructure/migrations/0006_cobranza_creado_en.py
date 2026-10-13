import django.utils.timezone
from django.db import migrations, models


def desde_la_facturacion(apps, schema_editor):
    """RF-VEN-69: las cobranzas ya creadas toman la fecha y hora de facturación del pedido."""
    Cobranza = apps.get_model("sales", "Cobranza")
    for c in Cobranza.all_tenants.select_related("pedido"):
        cuando = c.pedido.facturado_en or c.pedido.creado_en
        Cobranza.all_tenants.filter(pk=c.pk).update(creado_en=cuando)


class Migration(migrations.Migration):
    dependencies = [("sales", "0005_segregacion_cobranza")]

    operations = [
        migrations.AddField(
            model_name="cobranza",
            name="creado_en",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RunPython(desde_la_facturacion, migrations.RunPython.noop),
    ]
