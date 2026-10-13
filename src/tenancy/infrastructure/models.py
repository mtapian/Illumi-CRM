"""Modelos de tenancy (planes 0001a §2 y 0001b §2)."""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from shared.infrastructure.tenant_models import TenantModel
from tenancy.domain.suscripcion import Estado


class Plan(models.Model):
    nombre = models.CharField(max_length=80)
    slug = models.SlugField(max_length=40, unique=True)
    precio_mensual = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    limite_usuarios = models.PositiveIntegerField(null=True, blank=True)  # vacío = ilimitado
    limite_productos = models.PositiveIntegerField(null=True, blank=True)
    es_plan_prueba = models.BooleanField(default=False)
    dias_prueba = models.PositiveIntegerField(default=14)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["es_plan_prueba"],
                condition=Q(es_plan_prueba=True, activo=True),
                name="un_plan_de_prueba_activo",
            )
        ]

    def __str__(self):
        return self.nombre


class Empresa(models.Model):
    # El RUC no se edita (RF-TEN-17); trigger trg_empresa_ruc_inmutable.
    ruc = models.CharField(max_length=11, unique=True)
    razon_social = models.CharField(max_length=200)
    nombre_comercial = models.CharField(max_length=200, blank=True)
    direccion_fiscal = models.CharField(max_length=300, blank=True)
    ubigeo = models.CharField(max_length=6, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    logo = models.FileField(upload_to="logos/", blank=True)
    estado = models.CharField(max_length=10, choices=[(e, e) for e in Estado], default=Estado.TRIAL)
    estado_previo = models.CharField(max_length=10, blank=True)  # para reactivar (RF-TEN-22)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="empresas_plan")
    fecha_termino = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_comercial or self.razon_social


class ParametroVigencia(models.Model):
    """Parámetro con fecha de vigencia. `empresa` vacía = valor de la plataforma."""

    CLAVES = [
        ("igv_pct", "IGV %"),
        ("umbral_boleta_identificada", "Umbral de boleta identificada"),
        ("plazo_envio_dias", "Plazo de envío a SUNAT (días)"),
        ("retencion_anios", "Conservación de XML y CDR (años)"),
    ]
    empresa = models.ForeignKey(
        Empresa, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    clave = models.CharField(max_length=40, choices=CLAVES)
    valor = models.DecimalField(max_digits=14, decimal_places=4)
    vigente_desde = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "clave", "vigente_desde"],
                nulls_distinct=False,
                name="un_valor_por_ambito_clave_y_fecha",
            )
        ]

    def __str__(self):
        return f"{self.clave} = {self.valor} desde {self.vigente_desde}"


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password, **extra):
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email.strip())


class Usuario(AbstractBaseUser):
    email = models.EmailField(unique=True)  # se guarda en minúsculas
    nombre = models.CharField(max_length=150)
    empresa = models.ForeignKey(
        Empresa, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios"
    )
    is_active = models.BooleanField(default=True)
    is_super = models.BooleanField(default=False)  # super admin de la plataforma
    es_tecnico = models.BooleanField(default=False)  # dueño de tokens de API; no inicia sesión
    roles = models.ManyToManyField("Rol", through="UsuarioRol", related_name="usuarios")
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    objects = UsuarioManager()

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="email_unico")]

    def __str__(self):
        return self.email


# --- Catálogo de accesos (0001b): se sincroniza desde shared.domain.accesos al migrar ---


class Modulo(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=80)
    obsoleto = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


class Funcionalidad(models.Model):
    codigo = models.CharField(max_length=40, primary_key=True)
    nombre = models.CharField(max_length=80)
    modulo = models.ForeignKey(Modulo, on_delete=models.PROTECT, related_name="funcionalidades")
    obsoleto = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


class Permiso(models.Model):
    codigo = models.CharField(max_length=60, primary_key=True)
    funcionalidad = models.ForeignKey(Funcionalidad, on_delete=models.PROTECT, related_name="+")
    obsoleto = models.BooleanField(default=False)

    def __str__(self):
        return self.codigo


class FuncionalidadDependencia(models.Model):
    pk = models.CompositePrimaryKey("funcionalidad", "requiere")
    funcionalidad = models.ForeignKey(Funcionalidad, on_delete=models.PROTECT, related_name="+")
    requiere = models.ForeignKey(Funcionalidad, on_delete=models.PROTECT, related_name="+")

    def __str__(self):
        return f"{self.funcionalidad_id} requiere {self.requiere_id}"


class PlanFuncionalidad(models.Model):
    pk = models.CompositePrimaryKey("plan", "funcionalidad")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="+")
    funcionalidad = models.ForeignKey(Funcionalidad, on_delete=models.PROTECT, related_name="+")

    def __str__(self):
        return f"{self.plan_id}: {self.funcionalidad_id}"


class EmpresaAjuste(models.Model):
    """Excepción por empresa al plan. Dato de plataforma (constitución, art. 3.1)."""

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="ajustes")
    funcionalidad = models.ForeignKey(Funcionalidad, on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=7, choices=[("AGREGAR", "Agregar"), ("QUITAR", "Quitar")])
    vigente_hasta = models.DateField(null=True, blank=True)  # inclusiva (RN-TEN-08)
    motivo = models.CharField(max_length=300)
    creado_por = models.ForeignKey("Usuario", null=True, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    revocado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "funcionalidad"],
                condition=Q(revocado_en__isnull=True),
                name="un_ajuste_activo_por_funcionalidad",
            )
        ]

    def __str__(self):
        return f"{self.tipo} {self.funcionalidad_id}"


class Actividad(models.Model):
    """Registro de acciones del super admin sobre una empresa. Solo inserción."""

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="+")
    actor = models.ForeignKey("Usuario", null=True, on_delete=models.PROTECT, related_name="+")
    accion = models.CharField(max_length=40)
    motivo = models.CharField(max_length=300, blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.accion} ({self.created_at:%Y-%m-%d})"


# --- Roles y permisos de cada empresa (0001c) ---


class Rol(TenantModel):
    nombre = models.CharField(max_length=80)
    es_sistema = models.BooleanField(default=False)  # "Administrador": no se edita (RF-TEN-37)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nombre"], name="rol_nombre_unico"),
            models.UniqueConstraint(
                fields=["empresa"], condition=Q(es_sistema=True), name="un_rol_de_sistema"
            ),
        ]

    def __str__(self):
        return self.nombre


class RolPermiso(models.Model):
    """Se conserva aunque el permiso deje de estar habilitado (RF-TEN-39)."""

    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="permisos")
    permiso = models.ForeignKey(Permiso, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["rol", "permiso"], name="rol_permiso_unico")]

    def __str__(self):
        return f"{self.rol_id}: {self.permiso_id}"


class UsuarioRol(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="+")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["usuario", "rol"], name="usuario_rol_unico")]

    def __str__(self):
        return f"{self.usuario_id}: {self.rol_id}"


# --- Auditoría de accesos y tokens de API (0001d) ---


def _ahora():
    return timezone.now()


class AuditoriaAcceso(TenantModel):
    """Quién cambió qué acceso, cuándo, y el valor anterior y el nuevo. Solo inserción."""

    ENTIDADES = [(e, e) for e in ("ROL", "USUARIO_ROL", "USUARIO", "TOKEN_API")]
    actor = models.ForeignKey(Usuario, null=True, on_delete=models.PROTECT, related_name="+")
    entidad = models.CharField(max_length=12, choices=ENTIDADES)
    entidad_id = models.BigIntegerField()
    accion = models.CharField(max_length=20)
    antes = models.JSONField(null=True, blank=True)
    despues = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=_ahora)

    def __str__(self):
        return f"{self.entidad} {self.accion} ({self.created_at:%Y-%m-%d})"


class ApiToken(TenantModel):
    """Solo se guarda el hash SHA-256: el token no se puede recuperar en claro (RNF-TEN-02)."""

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="tokens")
    nombre = models.CharField(max_length=80)
    token_hash = models.CharField(max_length=64, unique=True)
    prefijo = models.CharField(max_length=8)
    creado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    ultimo_uso_en = models.DateTimeField(null=True, blank=True)
    revocado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.prefijo}…)"


class TipoDocumento(models.Model):
    """Maestro de tipos de documento de identidad de la plataforma (0006a, RF-VEN-49;
    catálogo 06 de SUNAT). Lo mantiene el super admin; no se elimina."""

    abreviatura = models.CharField(max_length=10, unique=True)
    codigo_sunat = models.CharField(max_length=2, unique=True)
    nombre = models.CharField(max_length=60)
    exige_numero = models.BooleanField(default=True)
    longitud_min = models.PositiveSmallIntegerField(default=1)
    longitud_max = models.PositiveSmallIntegerField(default=15)
    caracteres = models.CharField(max_length=12, default="ALFANUMERICO")
    validacion = models.CharField(max_length=10, default="NINGUNA")
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(longitud_min__lte=F("longitud_max"))
                & (Q(exige_numero=True) | Q(longitud_min=0, longitud_max=0)),
                name="tipo_documento_longitud",
            )
        ]

    def __str__(self):
        return self.nombre
