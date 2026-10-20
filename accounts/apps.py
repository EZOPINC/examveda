"""Register the account workflow that extends Django's built-in user system."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configure the account workflow app without replacing Django users."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Student accounts"
