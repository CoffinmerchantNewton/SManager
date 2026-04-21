import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
if "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_celery_beat",
    "pollen.apps.core",
    "pollen.apps.forecast",
    "pollen.apps.workflows",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "pollen" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pollen.apps.core.context_processors.shell_context",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "pollen_portal"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = os.getenv("APP_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "pollen" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_ROOT = Path(os.getenv("POLLEN_DATA_ROOT", BASE_DIR / "data"))
RUNS_ROOT = DATA_ROOT / "runs"
PRODUCTS_ROOT = DATA_ROOT / "products"
LOGS_ROOT = DATA_ROOT / "logs"
for directory in (DATA_ROOT, RUNS_ROOT, PRODUCTS_ROOT, LOGS_ROOT, MEDIA_ROOT):
    directory.mkdir(parents=True, exist_ok=True)

SITE_TITLE = os.getenv("SITE_TITLE", "中国花粉传播预报系统")
SITE_SUBTITLE = os.getenv(
    "SITE_SUBTITLE",
    "基于 WRF-Chem / WRF-Pollen 的全域花粉传播预报与自动化业务运行平台",
)
SITE_COPYRIGHT = os.getenv("SITE_COPYRIGHT", "Copyright 2026 Pollen Forecast Center")
CONSOLE_PASSWORD = os.getenv("CONSOLE_PASSWORD", "admin123")
SIMULATE_SLURM = env_bool("SIMULATE_SLURM", True)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True

WRF_ROOT = os.getenv("WRF_ROOT", "/opt/wrf")
WPS_ROOT = os.getenv("WPS_ROOT", "/opt/wps")
WRF_POLLEN_ROOT = os.getenv("WRF_POLLEN_ROOT", "/opt/wrf-pollen")
SHARED_INPUT_ROOT = os.getenv("SHARED_INPUT_ROOT", "/data/wrf-inputs")
SHARED_OUTPUT_ROOT = os.getenv("SHARED_OUTPUT_ROOT", str(PRODUCTS_ROOT))

DEFAULT_FORECAST_STEPS = json.dumps(
    [
        "geogrid",
        "ungrib",
        "metgrid",
        "wps",
        "pollen_interp",
        "wrf",
        "postprocess",
    ]
)
