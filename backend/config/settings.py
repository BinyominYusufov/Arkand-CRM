"""
Настройки проекта ARKAND · Часть 6 — Финансы.

SQLite с обязательными PRAGMA (WAL, foreign_keys, busy_timeout) и
transaction_mode=IMMEDIATE (Django 5.1+) — см. ТЗ, раздел 2.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "ARKAND_SECRET_KEY",
    "django-insecure-arkand-dev-only-not-for-production",
)

DEBUG = os.environ.get("ARKAND_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "corsheaders",
    "rest_framework",
    "django_filters",
    # ARKAND apps
    "apps.core",
    "apps.accounts",
    "apps.audit",
    "apps.finance",
    "apps.cash",
    "apps.settlements",
    "apps.payroll",
    "apps.reports",
    "apps.overlay",
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
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

# --- База данных: SQLite (обязательная настройка из ТЗ, раздел 2) ---
# ARKAND_DB_NAME позволяет E2E-прогонам работать на отдельном файле БД.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.environ.get("ARKAND_DB_NAME", "db.sqlite3"),
        "OPTIONS": {
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA foreign_keys=ON;"
                "PRAGMA busy_timeout=5000;"
            ),
            "transaction_mode": "IMMEDIATE",  # Django 5.1+: снижает конфликты записи
        },
    }
}

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Dushanbe"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "EXCEPTION_HANDLER": "apps.core.exceptions.drf_exception_handler",
    # Деньги (Decimal) сериализуются строкой — поведение DRF по умолчанию,
    # фиксируем его явно (ТЗ, раздел 2).
    "COERCE_DECIMAL_TO_STRING": True,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOW_ALL_ORIGINS = True  # dev-режим; фронтенд на Vite (5173)

# Точка расширения под фоновые задачи (Celery НЕ вводим на этом этапе — ТЗ).
# Тяжёлые расчёты (зарплата, отчёты) выполняются синхронно в services.
