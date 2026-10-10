from pathlib import Path

from django.db import migrations

SQL = (Path(__file__).resolve().parent.parent / "sql" / "isc_inmutable.sql").read_text()


class Migration(migrations.Migration):
    # fn_rechazar_cambio() la crea tenancy (0002_inmutables).
    dependencies = [("catalog", "0003_isc"), ("tenancy", "0002_inmutables")]
    operations = [
        migrations.RunSQL(SQL, "DROP TRIGGER IF EXISTS trg_isc_tarifa_inmutable ON catalog_isctarifa;")
    ]
