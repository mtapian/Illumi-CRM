from pathlib import Path

from django.db import migrations

SQL = (Path(__file__).resolve().parent.parent / "sql" / "inmutables.sql").read_text()

REVERSE = """
DROP TRIGGER IF EXISTS trg_empresa_ruc_inmutable ON tenancy_empresa;
DROP TRIGGER IF EXISTS trg_parametro_vigencia_inmutable ON tenancy_parametrovigencia;
DROP FUNCTION IF EXISTS fn_ruc_inmutable();
DROP FUNCTION IF EXISTS fn_rechazar_cambio();
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
