"""Register the small shared access policy used by content and exam views."""

from django.apps import AppConfig


class AccessControlConfig(AppConfig):
    """Configure the shared policy app without adding roles or entitlement tables."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "access_control"
    verbose_name = "Access policies"
