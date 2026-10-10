"""Sincroniza el catálogo de accesos (código) con sus tablas en cada `migrate`.

Idempotente: crea o actualiza lo que está en `CATALOGO` y marca `obsoleto` lo retirado,
sin borrarlo, porque puede estar referenciado por planes, ajustes o roles (RF-TEN-25).
"""

from django.db import transaction

from shared.domain.accesos import CATALOGO, MODULOS
from tenancy.infrastructure.models import (
    Funcionalidad,
    FuncionalidadDependencia,
    Modulo,
    Permiso,
)


@transaction.atomic
def sincronizar_catalogo(**_):
    for codigo, nombre in MODULOS.items():
        Modulo.objects.update_or_create(
            codigo=codigo, defaults={"nombre": nombre, "obsoleto": False}
        )
    for f in CATALOGO.values():
        Funcionalidad.objects.update_or_create(
            codigo=f.codigo, defaults={"nombre": f.nombre, "modulo_id": f.modulo, "obsoleto": False}
        )
        for p in f.permisos:
            Permiso.objects.update_or_create(
                codigo=p, defaults={"funcionalidad_id": f.codigo, "obsoleto": False}
            )
    FuncionalidadDependencia.objects.all().delete()
    FuncionalidadDependencia.objects.bulk_create(
        FuncionalidadDependencia(funcionalidad_id=f.codigo, requiere_id=r)
        for f in CATALOGO.values()
        for r in f.requiere
    )
    permisos = {p for f in CATALOGO.values() for p in f.permisos}
    Modulo.objects.exclude(codigo__in=MODULOS).update(obsoleto=True)
    Funcionalidad.objects.exclude(codigo__in=CATALOGO).update(obsoleto=True)
    Permiso.objects.exclude(codigo__in=permisos).update(obsoleto=True)
