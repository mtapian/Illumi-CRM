from pathlib import Path

from django.db import migrations

SQL = (Path(__file__).resolve().parent.parent / "sql" / "auditoria_inmutable.sql").read_text()
REVERSE = "DROP TRIGGER IF EXISTS trg_auditoria_acceso_inmutable ON tenancy_auditoriaacceso;"


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0008_auditoria_tokens")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
