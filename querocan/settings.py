"""
Configuración de Django para QueroCan.

Todos os valores que cambian entre desenvolvemento e produción (claves, base de
datos, correo...) lense de variables de contorno, definidas no ficheiro .env.
Consulta .env.exemplo para ver a lista completa.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(nome, por_defecto=""):
    """Le unha variable de contorno como texto."""
    return os.environ.get(nome, por_defecto)


def _env_bool(nome, por_defecto=False):
    """Le unha variable de contorno como booleano ("1", "true", "si" → True)."""
    valor = os.environ.get(nome)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in {"1", "true", "si", "yes"}


SECRET_KEY = _env("DJANGO_SECRET_KEY", "clave-so-para-desenvolvemento")
DEBUG = _env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h.strip() for h in _env("DJANGO_ALLOWED_HOSTS", "localhost").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps de QueroCan
    "querocan",
    "contas",
    "compatibilidade",
    "contido",
    "animais",
    "adopcions",
    "xestion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# En produción WhiteNoise serve os estáticos recollidos con collectstatic
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "querocan.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "querocan.wsgi.application"

# Base de datos MySQL (servizo «db» de compose.yaml)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": _env("MYSQL_DATABASE", "querocan"),
        "USER": _env("MYSQL_USER", "querocan"),
        "PASSWORD": _env("MYSQL_PASSWORD", "querocan"),
        "HOST": _env("MYSQL_HOST", "db"),
        "PORT": _env("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
        "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
    }
}

# Modelo de usuario propio (entrada por correo e campo «rol»)
AUTH_USER_MODEL = "contas.Usuario"
LOGIN_URL = "contas:entrar"
LOGIN_REDIRECT_URL = "contido:landing"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Idioma e zona horaria: a interface está só en galego
LANGUAGE_CODE = "gl"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# Ficheiros estáticos (CSS, JS, fontes) e subidos (fotos dos cans)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Enderezo público da web (para as ligazóns dos correos)
SITIO_URL = _env("SITIO_URL", "http://localhost:8000")

# Correo
EMAIL_BACKEND = _env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = _env("EMAIL_HOST")
EMAIL_PORT = int(_env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = _env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = _env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = _env("DEFAULT_FROM_EMAIL", "QueroCan <ola@querocan.local>")
