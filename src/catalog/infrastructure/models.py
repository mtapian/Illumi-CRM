"""Modelos del catálogo (plan 0002a §2). La base refuerza las reglas del dominio."""

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from catalog.domain.impuestos import AFECTACION, COMPRA, FIJO, ISC, PORCENTAJE, VENTA
from catalog.domain.tipos import TipoProducto as T
from shared.infrastructure.tenant_models import TenantModel


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


class Categoria(TenantModel):
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "empresa", Lower("nombre"), name="categoria_unica_sin_mayusculas"
            )
        ]

    def __str__(self):
        return self.nombre


class Marca(TenantModel):
    """Marca opcional del producto (RF-CAT-33)."""

    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint("empresa", Lower("nombre"), name="marca_unica_sin_mayusculas")
        ]

    def __str__(self):
        return self.nombre


class Producto(TenantModel):
    """Bien o servicio con sus casillas de gestión (spec 0002a, enmienda 4)."""

    sku = models.CharField(max_length=40)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=12, choices=[(t, t) for t in T], default=T.BIEN)
    se_vende = models.BooleanField(default=False)
    se_compra = models.BooleanField(default=True)  # un bien nuevo se compra (RF-CAT-38)
    se_fabrica = models.BooleanField(default=False)
    unidad = models.ForeignKey(Unidad, on_delete=models.PROTECT, related_name="productos")
    categoria = models.ForeignKey(
        Categoria, null=True, blank=True, on_delete=models.PROTECT, related_name="productos"
    )
    marca = models.ForeignKey(
        Marca, null=True, blank=True, on_delete=models.PROTECT, related_name="productos"
    )
    stock_minimo = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    contenido_litros = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    # ISC en la ficha (enmienda 4, RF-CAT-45): None = no afecto; tasas en ProductoIscTasa.
    isc_sistema = models.CharField(max_length=12, null=True, blank=True)  # noqa: DJ001 (NULL = no afecto; el CHECK lo usa)
    isc_codigo_tipo_sistema = models.CharField(max_length=2, blank=True)
    vida_util_dias = models.PositiveIntegerField(null=True, blank=True)
    peso_kg = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    volumen_m3 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    referencia = models.CharField(max_length=60, blank=True)  # RF-CAT-31
    codigo_barras = models.CharField(max_length=40, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "sku"], name="sku_unico_por_empresa"),
            models.UniqueConstraint(  # RF-CAT-31: vacío permitido en varios
                fields=["empresa", "codigo_barras"],
                condition=~Q(codigo_barras=""),
                name="codigo_barras_unico",
            ),
            models.CheckConstraint(condition=Q(tipo__in=list(T)), name="tipo_bien_o_servicio"),
            models.CheckConstraint(  # RF-CAT-38
                condition=Q(se_vende=True) | Q(se_compra=True) | Q(se_fabrica=True),
                name="al_menos_una_casilla",
            ),
            models.CheckConstraint(  # RF-CAT-37: un servicio no se fabrica ni tiene inventario
                condition=~Q(tipo=T.SERVICIO)
                | Q(se_fabrica=False, peso_kg__isnull=True, volumen_m3__isnull=True),
                name="servicio_sin_fabricacion_ni_inventario",
            ),
            models.CheckConstraint(  # RF-CAT-39: precio si y solo si se vende
                # IS NOT NULL explícito: en PostgreSQL un CHECK que da NULL se acepta.
                condition=Q(se_vende=True, precio_venta__isnull=False, precio_venta__gt=0)
                | Q(se_vende=False, precio_venta__isnull=True),
                name="precio_si_se_vende",
            ),
            models.CheckConstraint(
                condition=Q(vida_util_dias__isnull=True) | Q(vida_util_dias__gt=0),
                name="vida_util_positiva",
            ),
            models.CheckConstraint(  # RF-CAT-23, 26, 45: solo bienes que se venden, por litro
                condition=Q(isc_sistema__isnull=True)
                | Q(
                    isc_sistema="ESPECIFICO",
                    tipo=T.BIEN,
                    se_vende=True,
                    contenido_litros__isnull=False,
                    contenido_litros__gt=0,
                ),
                name="isc_solo_bien_vendible_por_litro",
            ),
        ]
        indexes = [models.Index(fields=["empresa", "activo", "tipo"])]

    def __str__(self):
        return f"{self.sku} · {self.nombre}"


class ProductoIscTasa(TenantModel):
    """Tasa de ISC de un producto con su vigencia (RF-CAT-46). Solo inserción (trigger).
    `producto_id` sin FK, como el historial: sobrevive a la eliminación del producto."""

    producto_id = models.BigIntegerField(db_index=True)
    vigente_desde = models.DateField()
    monto_por_litro = models.DecimalField(max_digits=10, decimal_places=4)
    creado_por = models.ForeignKey(
        "tenancy.Usuario", null=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["producto_id", "vigente_desde"], name="tasa_isc_por_fecha"
            ),
            models.CheckConstraint(condition=Q(monto_por_litro__gt=0), name="tasa_isc_positiva"),
        ]

    def __str__(self):
        return f"{self.monto_por_litro} desde {self.vigente_desde}"


class Impuesto(TenantModel):
    """Impuesto de venta o de compra de la empresa (spec 0002e, RF-CAT-53). Sus importes
    están en las tasas: % o S/ por unidad según el criterio que elige el usuario (enmienda 1)."""

    nombre = models.CharField(max_length=80)
    tipo = models.CharField(max_length=6, choices=[(t, t) for t in (VENTA, COMPRA)])
    codigo = models.CharField(max_length=3, choices=[(c, c) for c in (*AFECTACION, ISC)])
    criterio = models.CharField(
        max_length=10, choices=[(c, c) for c in (PORCENTAJE, FIJO)], default=PORCENTAJE
    )
    activo = models.BooleanField(default=True)
    productos = models.ManyToManyField(
        "Producto", through="ProductoImpuesto", related_name="impuestos"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "empresa", "tipo", Lower("nombre"), name="impuesto_unico_por_tipo"
            ),
            models.CheckConstraint(condition=Q(tipo__in=[VENTA, COMPRA]), name="impuesto_tipo"),
            models.CheckConstraint(
                condition=Q(codigo__in=[*AFECTACION, ISC]), name="impuesto_codigo"
            ),
            models.CheckConstraint(
                condition=~Q(codigo=ISC) | Q(tipo=VENTA), name="isc_solo_de_venta"
            ),
            models.CheckConstraint(
                condition=Q(criterio__in=[PORCENTAJE, FIJO]), name="impuesto_criterio"
            ),
        ]

    def __str__(self):
        return self.nombre


class ImpuestoTasa(TenantModel):
    """Importe de un impuesto con su vigencia (RF-CAT-54): % o S/ por unidad. Solo inserción."""

    impuesto = models.ForeignKey(Impuesto, on_delete=models.PROTECT, related_name="tasas")
    vigente_desde = models.DateField()
    importe = models.DecimalField(max_digits=10, decimal_places=4)
    creado_por = models.ForeignKey(
        "tenancy.Usuario", null=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["impuesto", "vigente_desde"], name="impuesto_tasa_por_fecha"
            ),
            models.CheckConstraint(condition=Q(importe__gte=0), name="impuesto_tasa_no_negativa"),
        ]


class ProductoImpuesto(TenantModel):
    """Impuesto asignado a un producto (RF-CAT-56); la lista (venta o compra) es su tipo."""

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    impuesto = models.ForeignKey(Impuesto, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["producto", "impuesto"], name="producto_impuesto_unico")
        ]


class ProductoHistorial(TenantModel):
    """Historial del producto (RF-CAT-32). Solo inserción (trigger). `producto_id` sin FK:
    el historial sobrevive a la eliminación de un producto sin movimientos."""

    producto_id = models.BigIntegerField(db_index=True)
    actor = models.ForeignKey(
        "tenancy.Usuario", null=True, on_delete=models.PROTECT, related_name="+"
    )
    accion = models.CharField(max_length=20)
    antes = models.JSONField(null=True)
    despues = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.producto_id} {self.accion}"


class RecetaComponente(models.Model):
    """Receta opcional de un bien que se fabrica: cualquier producto activo, cantidad por
    unidad (RF-CAT-41). Pertenece a la empresa de su producto."""

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="receta")
    componente = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="+")
    cantidad_por_unidad = models.DecimalField(max_digits=14, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["producto", "componente"], name="componente_unico"),
            models.CheckConstraint(
                condition=~Q(producto=F("componente")), name="componente_no_es_el_producto"
            ),
            models.CheckConstraint(
                condition=Q(cantidad_por_unidad__gt=0), name="cantidad_componente_positiva"
            ),
        ]

    def __str__(self):
        return f"{self.componente_id} × {self.cantidad_por_unidad}"
