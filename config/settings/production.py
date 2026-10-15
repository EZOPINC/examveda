"""Configure production security and PostgreSQL requirements.

Production startup fails closed when secrets, allowed hosts, or database settings
are missing so a deployment cannot silently run with development defaults.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


DEBUG = False
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain production host names.")

required_database_settings = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST")
missing_database_settings = [
    setting_name
    for setting_name in required_database_settings
    if not os.environ.get(setting_name)
]
if missing_database_settings:
    missing_names = ", ".join(missing_database_settings)
    raise ImproperlyConfigured(
        f"Production PostgreSQL configuration is incomplete: {missing_names}."
    )

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 5},
    }
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
