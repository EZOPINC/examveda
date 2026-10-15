"""Configure safe, convenient settings for local development.

This module is selected by manage.py by default. SQLite keeps the first-run path
available without a local PostgreSQL service; setting DB_NAME opts into PostgreSQL.
"""

import os
import secrets

from .base import *  # noqa: F403


DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

if os.environ.get("DB_NAME"):
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"connect_timeout": 5},
        }
    }
