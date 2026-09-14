"""
Configuración base de Django para el proyecto de Software Educativo de Sistemas Expertos.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta raíz del proyecto (directorio 'back')
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar variables de entorno desde .env
load_dotenv(BASE_DIR / ".env")

# Seguridad y Claves
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

ALLOWED_HOSTS = ["*"]

# Aplicaciones instaladas
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # Módulos propios del monolito modular
    "apps.sistemas_expertos.apps.SistemasExpertosConfig",
    "apps.base_conocimiento.apps.BaseConocimientoConfig",
    "apps.editor_visual.apps.EditorVisualConfig",
    "apps.inferencia.apps.InferenciaConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Base de datos
DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.postgresql")
DB_NAME = os.getenv("DB_NAME", "sistemas_expertos_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

if "sqlite" in DB_ENGINE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / DB_NAME,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }

# Clave primaria por defecto con UUID
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Internacionalización y zona horaria
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "compartido.paginacion.paginacion_personalizada.PaginacionEstandar",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "compartido.excepciones.manejadores.manejador_excepciones_global",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# Swagger / OpenAPI con drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "API Software Educativo de Sistemas Expertos",
    "DESCRIPTION": (
        "Backend del Software Educativo Interactivo de Apoyo Docente "
        "para la Enseñanza de Sistemas Expertos (Sprint 1)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# Parámetros del motor de inferencia
MAX_INFERENCE_ITERATIONS = int(os.getenv("MAX_INFERENCE_ITERATIONS", "100"))

# Configuración de Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} [{name}:{lineno}] {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "motor_inferencia": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
