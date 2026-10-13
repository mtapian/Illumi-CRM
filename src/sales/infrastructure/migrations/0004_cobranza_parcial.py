from django.db import migrations, models
from django.db.models import F, Q


def parciales(apps, schema_editor):
    """Las cobranzas Pendientes con algo pagado pasan a Parcial (PO, 2026-10-13)."""
    Cobranza = apps.get_model("sales", "Cobranza")
    Cobranza.all_tenants.filter(estado="PENDIENTE", pagado__gt=0).update(estado="PARCIAL")


def pendientes(apps, schema_editor):
    apps.get_model("sales", "Cobranza").all_tenants.filter(estado="PARCIAL").update(
        estado="PENDIENTE"
    )


class Migration(migrations.Migration):
    dependencies = [("sales", "0003_codigo_cobranza")]

    operations = [
        migrations.RemoveConstraint(model_name="cobranza", name="cobranza_estado_segun_pagado"),
        migrations.RemoveConstraint(model_name="cobranza", name="cobranza_pagado_valido"),
        migrations.RunPython(parciales, pendientes),
        migrations.AddConstraint(
            model_name="cobranza",
            constraint=models.CheckConstraint(
                condition=Q(
                    estado__in=("PENDIENTE", "PARCIAL", "PAGADA"),
                    pagado__gte=0,
                    pagado__lte=F("total"),
                ),
                name="cobranza_pagado_valido",
            ),
        ),
        migrations.AddConstraint(
            model_name="cobranza",
            constraint=models.CheckConstraint(
                condition=Q(estado="PAGADA", pagado=F("total"))
                | Q(estado="PENDIENTE", pagado=0)
                | (Q(estado="PARCIAL", pagado__gt=0) & ~Q(pagado=F("total"))),
                name="cobranza_estado_segun_pagado",
            ),
        ),
    ]
