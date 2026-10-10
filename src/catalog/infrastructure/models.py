"""Modelos del catálogo (plan 0002a §2). La base refuerza las reglas del dominio."""

from django.db import models
from django.db.models import Q

from catalog.domain.tipos import TipoProducto as T
from shared.infrastructure.tenant_models import TenantModel

VENDIBLES = [t for t in T if t.vendible]
CON_LOTE = [t for t in T if t.lote_siempre]


class Unidad(TenantModel):
    nombre = models.CharField(max_length=40)
    abreviatura = models.CharField(max_length=10)
    codigo_sunat = models.CharField(max_length=3)  # catálogo 03 de SUNAT (NIU, KGM…)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "abreviatura"], name="unidad_unica")
        ]

    def __str__(self):
        return self.abreviatura


class Familia(TenantModel):
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["empresa", "nombre"], name="familia_unica")]

    def __str__(self):
        return self.nombre


class IscCategoria(TenantModel):
    """Categoría de ISC de la empresa (spec 0002c). Solo Sistema Específico en el MVP."""

    nombre = models.CharField(max_length=80)
    sistema = models.CharField(max_length=12, default="ESPECIFICO")
    codigo_tributo = models.CharField(max_length=4, default="2000")
    # Dato configurable (PO, 2026-10-10): el contador indicó 01, el catálogo 08 indica 02.
    codigo_tipo_sistema = models.CharField(max_length=2)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nombre"], name="isc_categoria_unica"),
            models.CheckConstraint(condition=Q(sistema="ESPECIFICO"), name="isc_solo_especifico"),
        ]

    def __str__(self):
        return self.nombre


class IscTarifa(models.Model):
    """Monto por litro con vigencia. Solo inserción (trigger; RN-CAT-10)."""

    categoria = models.ForeignKey(IscCategoria, on_delete=models.PROTECT, related_name="tarifas")
    vigente_desde = models.DateField()
    monto_por_litro = models.DecimalField(max_digits=10, decimal_places=4)
    creado_por = models.ForeignKey(
        "tenancy.Usuario", null=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["categoria", "vigente_desde"], name="tarifa_por_fecha"),
            models.CheckConstraint(condition=Q(monto_por_litro__gt=0), name="tarifa_positiva"),
        ]

    def __str__(self):
        return f"{self.monto_por_litro} desde {self.vigente_desde}"


class Producto(TenantModel):
    sku = models.CharField(max_length=40)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=12, choices=[(t, t) for t in T])
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="productos")
    familia = models.ForeignKey(
        Familia, null=True, blank=True, on_delete=models.PROTECT, related_name="productos"
    )
    stock_minimo = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    controla_lote = models.BooleanField(default=False)
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    contenido_litros = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    isc_categoria = models.ForeignKey(
        IscCategoria, null=True, blank=True, on_delete=models.PROTECT, related_name="productos"
    )
    vida_util_dias = models.PositiveIntegerField(null=True, blank=True)
    prefijo_lote = models.CharField(max_length=10, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "sku"], name="sku_unico_por_empresa"),
            models.CheckConstraint(condition=Q(tipo__in=list(T)), name="tipo_valido"),
            models.CheckConstraint(  # RF-CAT-13: precio solo y siempre en vendibles
                # IS NOT NULL explícito: en PostgreSQL un CHECK que da NULL se acepta.
                condition=Q(tipo__in=VENDIBLES, precio_venta__isnull=False, precio_venta__gt=0)
                | (~Q(tipo__in=VENDIBLES) & Q(precio_venta__isnull=True)),
                name="precio_solo_en_vendibles",
            ),
            models.CheckConstraint(  # RN-CAT-09
                condition=~Q(tipo=T.TERMINADO)
                | Q(vida_util_dias__isnull=False, vida_util_dias__gt=0),
                name="terminado_con_vida_util",
            ),
            models.CheckConstraint(  # RF-CAT-12
                condition=Q(tipo__in=CON_LOTE, controla_lote=True)
                | Q(tipo=T.MERCADERIA)
                | Q(tipo__in=[T.INSUMO, T.ENVASE], controla_lote=False),
                name="lote_segun_tipo",
            ),
        ]
        indexes = [models.Index(fields=["empresa", "activo", "tipo"])]

    def __str__(self):
        return f"{self.sku} · {self.nombre}"


class Presentacion(TenantModel):
    """Un TERMINADO = granel × contenido + materiales por unidad (spec 0002b)."""

    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name="presentacion")
    granel = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="presentaciones")
    contenido_litros = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(contenido_litros__gt=0), name="contenido_positivo")
        ]

    def __str__(self):
        return f"{self.producto_id}: {self.contenido_litros} L"


class PresentacionMaterial(models.Model):
    presentacion = models.ForeignKey(
        Presentacion, on_delete=models.CASCADE, related_name="materiales"
    )
    material = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="+")
    cantidad_por_unidad = models.DecimalField(max_digits=14, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["presentacion", "material"], name="material_unico"),
            models.CheckConstraint(
                condition=Q(cantidad_por_unidad__gt=0), name="cantidad_material_positiva"
            ),
        ]

    def __str__(self):
        return f"{self.material_id} × {self.cantidad_por_unidad}"
