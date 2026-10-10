from pathlib import Path

from django.db import migrations

SQL = (Path(__file__).resolve().parent.parent / "sql" / "secuencia.sql").read_text()


class Migration(migrations.Migration):
    dependencies = [("shared", "0001_initial")]
    operations = [
        migrations.RunSQL(
            SQL, "DROP FUNCTION IF EXISTS fn_siguiente_correlativo(bigint, text, text);"
        )
    ]
