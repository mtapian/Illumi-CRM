from django.db import migrations, models


def numerar(apps, schema_editor):
    """Las cobranzas ya creadas reciben su código en orden de creación, por empresa, con el
    mismo correlativo que usarán las nuevas."""
    Cobranza = apps.get_model("sales", "Cobranza")
    with schema_editor.connection.cursor() as cursor:
        for c in Cobranza.all_tenants.order_by("id"):
            cursor.execute(
                "SELECT fn_siguiente_correlativo(%s, 'COBRANZA', '')", [c.empresa_id]
            )
            Cobranza.all_tenants.filter(pk=c.pk).update(numero=cursor.fetchone()[0])


def olvidar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DELETE FROM shared_secuencia WHERE documento = 'COBRANZA'")


class Migration(migrations.Migration):
    dependencies = [("sales", "0002_facturacion_cobranza"), ("shared", "0002_fn_siguiente_correlativo")]

    operations = [
        migrations.AddField(
            model_name="cobranza", name="numero", field=models.IntegerField(null=True)
        ),
        migrations.RunPython(numerar, olvidar),
        migrations.AlterField(model_name="cobranza", name="numero", field=models.IntegerField()),
        migrations.AddConstraint(
            model_name="cobranza",
            constraint=models.UniqueConstraint(
                fields=("empresa", "numero"), name="cobranza_numero_unico"
            ),
        ),
    ]
