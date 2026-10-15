"""Provide the command-line entry point for Django management tasks."""

import os
import sys


def main():
    """Run Django's management command using the selected settings module."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django could not be imported. Install the pinned packages from requirements.txt."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
