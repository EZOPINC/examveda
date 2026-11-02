"""Configure local development settings with PostgreSQL as the only database.

This module is selected by manage.py by default. It requires process-level
PostgreSQL configuration so local work cannot silently use a different database.
"""

import os
import secrets

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

required_database_settings = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST")
missing_database_settings = [
    setting_name
    for setting_name in required_database_settings
    if not os.environ.get(setting_name)
]
if missing_database_settings:
    missing_names = ", ".join(missing_database_settings)
    raise ImproperlyConfigured(
        f"Development PostgreSQL configuration is incomplete: {missing_names}. "
        "Load the local DB_* values into this process before running Django."
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
