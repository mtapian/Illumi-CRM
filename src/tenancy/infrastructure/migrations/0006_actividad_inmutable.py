from pathlib import Path

from django.db import migrations

SQL = (Path(__file__).resolve().parent.parent / "sql" / "actividad.sql").read_text()


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0005_accesos_plataforma")]
    operations = [
        migrations.RunSQL(SQL, "DROP TRIGGER IF EXISTS trg_actividad_inmutable ON tenancy_actividad;")
    ]
