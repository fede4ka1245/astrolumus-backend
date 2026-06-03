import os
from typing import List, Tuple

from datetime import timedelta
from pathlib import Path

import logging

from dotenv import load_dotenv

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import (
    BreadcrumbHandler,
    EventHandler,
    LoggingIntegration,
)

from django.utils.translation import gettext_lazy as _

from utils.minio import get_policy

from firebase_admin import initialize_app, credentials


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", default="0").lower() in ("true", "1")
HEADLESS = os.getenv("HEADLESS", default="0").lower() in ("true", "1")
DEBUG_TOOLBAR_CONFIG = {"RENDER_PANELS": False, "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEPLOY_DIR = BASE_DIR.parent
DOMAIN = os.getenv("DOMAIN")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split()
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS").split()
BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN")

INSTALLED_APPS = [
    "corsheaders",
    #"django.contrib.admin",
    "alpha.apps.AlphaAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "django_minio_backend.apps.DjangoMinioBackendConfig",  # https://github.com/theriverman/django-minio-backend
    # "rosetta",  # Replaced by Tolgee i18n Studio
    "voting",
    "notifications",
    "astroprocessor",
    "ordered_model",
    "users",
    "payments.apps.PaymentsConfig",
    "bootcamp.apps.BootcampConfig",
    "languages.apps.LanguagesConfig",
    "link.apps.LinkConfig",
    "horoscope.apps.HoroscopeConfig",
    "astrology_calendar.apps.AstrologyCalendarConfig",
    "astrology_forum.apps.AstrologyForumConfig",
    "favorite.apps.FavoriteConfig",
    "deep_sky.apps.DeepSkyConfig",
    "tariffs.apps.TariffsConfig",
    "assistant_quota.apps.AssistantQuotaConfig",
    "tarot.apps.TarotConfig",
    "advertising.apps.AdvertisingConfig",
    "chat.apps.ChatConfig",
    "complaints.apps.ComplaintsConfig",
    "stop_words.apps.StopWordsConfig",
    "info.apps.InfoConfig",
    "notifications_ext.apps.NotificationsExtConfig",
    "utils.apps.UtilsConfig",
    "analytics.apps.AnalyticsConfig",
    "consultations.apps.ConsultationsConfig",

    # Libs
    "fcm_django",
    "django_celery_beat",
    "drf_yasg",
    "ckeditor",
    "ckeditor_uploader",
    "debug_toolbar",
    "nested_admin",
    "colorfield",
    "django_admin_inline_paginator",
    "rangefilter",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "users.middleware.UserLanguageMiddleware",
    "users.middleware.last_seen_middleware",
    "users.middleware.restrict_access_middleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "alpha.urls"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "1000/minute",
        "forum.join": "1000/day",
        "memebership.create": "1000/day",
    }
    # "DEFAULT_VERSION": 1,
    # "ALLOWED_VERSIONS": [1],
}

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
                "utils.context_processors.tolgee_languages",
            ]
        },
    }
]

WSGI_APPLICATION = "alpha.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.User"
LAST_SEEN_INTERVAL = 60 * 30  # 30 minutes

LANGUAGES = [("en-us", _("US English")), ("ru", _("Russian"))]
LANGUAGE_CODE = "ru"  # when `LANGUAGES` is set, this is the default language
APP_LANGUAGE_MODEL = "users.AppLanguage"
TIME_ZONE = "Europe/Minsk"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "alpha/locale"]

STATIC_URL = "/static/"
# STATIC_ROOT can be overridden to match the web server static dir (e.g. /var/www/static)
STATIC_ROOT = os.getenv("STATIC_ROOT", "static")
WHITENOISE_USE_FINDERS = os.getenv("WHITENOISE_USE_FINDERS", "1").lower() in ("true", "1")
MEDIA_URL = "media/"
MEDIA_ROOT = DEPLOY_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        debug=DEBUG,
        integrations=[
            DjangoIntegration(
                middleware_spans=False,
                signals_spans=False,
            ),
            # disable logging integration
            LoggingIntegration(event_level=None, level=None),
        ],
        environment=os.getenv("SENTRY_ENV", default="Testing"),
    )

# add loguru instead of standard logging
LOGURU_DIAGNOSE = os.getenv("LOGURU_DIAGNOSE", default="0").lower() in ("true", "1")
logger.add(
    BreadcrumbHandler(level=logging.DEBUG),
    diagnose=LOGURU_DIAGNOSE,
    level=logging.DEBUG,
)
logger.add(
    EventHandler(level=logging.WARNING),
    diagnose=LOGURU_DIAGNOSE,
    level=logging.ERROR,
)

SWAGGER_SETTINGS = {"LOGIN_URL": "admin:login", "LOGOUT_URL": "admin:logout"}
# SWAGGER_SETTINGS = {"SECURITY_DEFINITIONS": {"basic": {"type": "basic"}}}

CKEDITOR_CONFIGS = {
    "default": {
        "width": "100%",
        "toolbar": "Custom",
        "toolbar_Custom": [
            ["Font", "FontSize", "Bold", "Italic", "Underline"],
            [
                "NumberedList",
                "BulletedList",
                "-",
                "Outdent",
                "Indent",
                "-",
                "JustifyLeft",
                "JustifyCenter",
                "JustifyRight",
                "JustifyBlock",
            ],
            ["Link", "Unlink", "Source"],
            ["RemoveFormat", "Image", "Iframe", "Table", "Youtube"],
            ["Maximize", "ShowBlocks"],
        ],
        "removePlugins": "stylesheetparser",
        "extraPlugins": ",".join(
            [
                "uploadimage",
                "div",
                "autolink",
                "autoembed",
                "autogrow",
                "widget",
                "lineutils",
                "clipboard",
                "dialog",
                "dialogui",
            ]
        ),
        "extraAllowedContent": "iframe[allowfullscreen,fullscreen]",
    },
    "readonly": {
        "readOnly": True,
        "toolbar": "Custom",
        "toolbar_Custom": [["Maximize"]],
    },
    "assignment_form": {
        "width": "100%",
        "toolbar": "Custom",
        "toolbar_Custom": [["Bold", "Italic", "Underline"], ["JustifyBlock"]],
        "extraPlugins": ",".join(["placeholder"]),
    },
}

CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_UPLOAD_PATH = "editor/uploads/"
CKEDITOR_FILENAME_GENERATOR = "config.ckeditor.filename"

# TODO not secure
CORS_ALLOW_ALL_ORIGINS = True

REDOC_SETTINGS = {"LAZY_RENDERING": False}

ASGI_APPLICATION = "alpha.asgi.application"

REDIS_URL = os.getenv("REDIS_URL")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
    },
    "analytics": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("ANALYTICS_DB_HOST", "analytics-db"),
        "PORT": os.getenv("ANALYTICS_DB_PORT", "5432"),
        "NAME": os.getenv("ANALYTICS_DB_NAME", "analytics"),
        "USER": os.getenv("ANALYTICS_DB_USER", "analytics"),
        "PASSWORD": os.getenv("ANALYTICS_DB_PASSWORD", "analytics123"),
    },
}

DATABASE_ROUTERS = ["analytics.db_router.AnalyticsRouter"]

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_PUBLIC_BUCKETS = os.getenv("MINIO_PUBLIC_BUCKETS").split()
MINIO_EXTERNAL_ENDPOINT = os.getenv("MINIO_EXTERNAL_ENDPOINT")
MINIO_EXTERNAL_ENDPOINT_USE_HTTPS = os.getenv("MINIO_EXTERNAL_ENDPOINT_USE_HTTPS", default="0").lower() in ("true", "1")
MINIO_USE_HTTPS = False
MINIO_URL_EXPIRY_HOURS = timedelta(days=1)  # Default is 7 days (longest) if not defined
MINIO_CONSISTENCY_CHECK_ON_START = True
MINIO_POLICY_HOOKS: List[Tuple[str, dict]] = [  # This array of (bucket_name, policy) tuples belong to Django settings
    (bucket, get_policy(bucket)) for bucket in MINIO_PUBLIC_BUCKETS
]
# MINIO_MEDIA_FILES_BUCKET = "my-media-files-bucket"  # replacement for MEDIA_ROOT
# MINIO_STATIC_FILES_BUCKET = "my-static-files-bucket"  # replacement for STATIC_ROOT
MINIO_BUCKET_CHECK_ON_SAVE = True  # Default: True // Creates bucket if missing, then save

# Celery
CELERY_BROKER_URL = os.getenv("REDIS_URL")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = {
    "sync-tolgee-to-s3": {
        "task": "utils.tasks.sync_tolgee_to_s3",
        "schedule": 300,  # every 5 minutes
    },
    "sync-analytics-db": {
        "task": "analytics.sync_to_analytics_db",
        "schedule": 3600,  # every hour
    },
}

# Email code lifetime
ACCESS_TOKEN_LIFETIME = timedelta(days=30)

# Simple JWT
SIMPLE_JWT = {
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "ROTATE_REFRESH_TOKENS": True,
}

# A list of all the people who get code error notifications.
ADMINS = [tuple(group.split()) for group in os.getenv("ADMINS").split("\n")]
SCHOOL_USER_ID = int(os.getenv("SCHOOL_USER_ID"))

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.timeweb.ru")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "2525"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() in ("true", "1")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() in ("true", "1")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# Mailtrap HTTP API (used when EMAIL_BACKEND points at MailtrapBackend)
MAILTRAP_API_TOKEN = os.getenv("MAILTRAP_API_TOKEN")
MAILTRAP_API_URL = os.getenv("MAILTRAP_API_URL")  # default: send.api.mailtrap.io/api/send
MAILTRAP_FROM_NAME = os.getenv("MAILTRAP_FROM_NAME", "Astrolumus")

# Resend HTTP API (used when EMAIL_BACKEND points at ResendBackend)
RESEND_API_TOKEN = os.getenv("RESEND_API_TOKEN")
RESEND_API_URL = os.getenv("RESEND_API_URL")  # default: api.resend.com/emails

SERVER_EMAIL = os.getenv("SERVER_EMAIL", "alphaspace@alpha-astro.com")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", SERVER_EMAIL)

SMS_API_KEY = os.getenv("SMS_API_KEY")
SMS_ALPHA_NAME = os.getenv("SMS_ALPHA_NAME")

BEPAID_SHOP_ID = os.getenv("BEPAID_SHOP_ID")
BEPAID_SECRET_KEY = os.getenv("BEPAID_SECRET_KEY")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "https://app.staging.alpha-astro.com/payment-success?session_id={CHECKOUT_SESSION_ID}")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "https://app.staging.alpha-astro.com/payment")
BEPAID_WEBHOOK_BASE_URL = os.getenv("BEPAID_WEBHOOK_BASE_URL", "https://backm.staging.alpha-astro.com")

J108_LOGIN = os.getenv("J108_LOGIN")
J108_PASSWORD = os.getenv("J108_PASSWORD")
J108_API_KEY = os.getenv("J108_API_KEY")
J108_API_URL = os.getenv("J108_API_URL", "https://j108.net/api")

YOOKASSA_ACCOUNT_ID = os.getenv("YOOKASSA_ACCOUNT_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

FIREBASE_APP = None
try:
    if os.getenv("FCM_PRIVATE_KEY"):
        FIREBASE_APP = initialize_app(
            credential=credentials.Certificate(
                {
                    "type": "service_account",
                    "project_id": os.getenv("FCM_PROJECT_ID"),
                    "private_key_id": os.getenv("FCM_PRIVATE_KEY_ID"),
                    "private_key": "\n".join(os.getenv("FCM_PRIVATE_KEY").split(r"\\n")),
                    "client_email": os.getenv("FCM_CLIENT_EMAIL"),
                    "client_id": os.getenv("FCM_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv("FCM_CLIENT_X509_CERT_URL"),
                    "universe_domain": "googleapis.com",
                }
            )
        )
except Exception:
    FIREBASE_APP = None

FCM_DJANGO_SETTINGS = {
    "DEFAULT_FIREBASE_APP": None,
    "APP_VERBOSE_NAME": "FCM",
    "ONE_DEVICE_PER_USER": False,
    "DELETE_INACTIVE_DEVICES": True,
}

DEFAULT_LANGUAGE_CODE = os.getenv("DEFAULT_LANGUAGE_CODE", "en")

# Tolgee i18n Studio
TOLGEE_API_URL = os.getenv("TOLGEE_API_URL", "http://tolgee:8085")
TOLGEE_API_KEY = os.getenv("TOLGEE_API_KEY", "")
TOLGEE_PROJECT_ID = int(os.getenv("TOLGEE_PROJECT_ID", "1"))  # main project (frontend, app-preview)
TOLGEE_TRANSLATIONS_S3_PREFIX = "translations"

# Per-entity Tolgee projects (each entity/namespace has its own project)
TOLGEE_PROJECTS = {
    "frontend": 19,
    "app-preview": 20,
    "tariffs": 3,
    "documents": 4,
    "app_info": 5,
    "astroprocessor_types": 22,
    "astroprocessor_data": 9,
    "sign_planet": 10,
    "planet_house": 11,
    "master_house": 12,
    "constellations": 13,
    "stellar_types": 21,
    "stars": 15,
    "sky_info": 16,
}

FEATURE_FLAG = os.getenv("FEATURE_FLAG", default="0").lower() in ("true", "1")

# Metabase embedding
METABASE_SITE_URL = os.getenv("METABASE_SITE_URL", "http://localhost:3001")
METABASE_SECRET_KEY = os.getenv("METABASE_SECRET_KEY", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(name)s %(process)d %(thread)d %(message)s"
        },
        "simple": {
            "format": "%(levelname)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
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
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}
