"""Register content taxonomy and editorial models in Django."""

from django.apps import AppConfig


class ContentConfig(AppConfig):
    """Configure the content app and its database default key type."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "content"
    verbose_name = "Free educational content"
