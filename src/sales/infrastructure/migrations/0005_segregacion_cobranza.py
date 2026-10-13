from django.db import migrations

NUEVOS = ("ventas.cobranza.anular", "ventas.metodo_pago.gestionar")


def segregar(apps, schema_editor):
    """RF-VEN-61 y 64: los roles que anulan ventas también anulan pagos y gestionan los
    métodos de pago (en una base nueva aún no hay roles)."""
    Permiso = apps.get_model("tenancy", "Permiso")
    RolPermiso = apps.get_model("tenancy", "RolPermiso")
    roles = list(
        RolPermiso.objects.filter(permiso_id="ventas.venta.anular").values_list(
            "rol_id", flat=True
        )
    )
    if not roles:
        return
    for codigo in NUEVOS:
        Permiso.objects.get_or_create(codigo=codigo, defaults={"funcionalidad_id": "ventas.ventas"})
        for rol_id in roles:
            RolPermiso.objects.get_or_create(rol_id=rol_id, permiso_id=codigo)


def revertir(apps, schema_editor):
    apps.get_model("tenancy", "RolPermiso").objects.filter(permiso_id__in=NUEVOS).delete()


class Migration(migrations.Migration):
    dependencies = [("sales", "0004_cobranza_parcial"), ("tenancy", "0011_umbral_boleta")]
    operations = [migrations.RunPython(segregar, revertir)]
