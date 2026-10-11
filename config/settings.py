import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-inseguro-solo-local")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "tenancy.infrastructure.apps.TenancyConfig",
    "catalog.infrastructure.apps.CatalogConfig",
    "purchasing.infrastructure.apps.PurchasingConfig",
    "shared.infrastructure.apps.SharedConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tenancy.interfaces.middleware.TenantMiddleware",
    "tenancy.interfaces.middleware.SuscripcionMiddleware",
    "tenancy.interfaces.acceso.AccesoMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": sorted(str(p) for p in (BASE_DIR / "src").glob("*/interfaces/templates")),
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tenancy.interfaces.context_processors.aviso_vencimiento",
                "shared.interfaces.menu.menu_lateral",
                "tenancy.interfaces.acceso.permisos",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "illumi"),
        "USER": os.environ.get("DB_USER", "illumi"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "illumi"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "54320"),
    }
}

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
FORMAT_MODULE_PATH = ["config.formats"]  # punto decimal (es_PE)
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "tenancy.Usuario"
AUTHENTICATION_BACKENDS = ["tenancy.infrastructure.auth_backend.EmailBackend"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
SERVIR_MEDIA = DEBUG or os.environ.get("DJANGO_SERVIR_MEDIA") == "1"

LOGIN_URL = "/login/"

# PRD Q6 (valores por defecto aprobados por el PO): contraseñas con los validadores estándar.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# RF-TEN-09: el enlace de recuperación vence en 60 minutos.
PASSWORD_RESET_TIMEOUT = 60 * 60
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)

# Seguridad (RNF-TEN-01, 03 y 04; plan 0000 §9).
# Contraseñas: hash PBKDF2 de Django (no reversible).
# PRD Q6 (valor por defecto aprobado): la sesión vence tras 8 horas de inactividad.
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True

# DJANGO_HTTPS=0 solo para el despliegue local de prueba por HTTP (docker-compose.yml).
if not DEBUG and os.environ.get("DJANGO_HTTPS", "1") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# API de integración (spec 0001d): cada vista declara su autenticación por token.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "UNAUTHENTICATED_USER": None,
}
