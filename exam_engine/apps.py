"""Register the mock examination domain with Django."""

from django.apps import AppConfig


class ExamEngineConfig(AppConfig):
    """Configure exam models and their default database key type."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "exam_engine"
    verbose_name = "Mock examination engine"
