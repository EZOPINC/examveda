"""Provide the minimal public pages required by the Django foundation.

The health endpoint intentionally avoids database probes and diagnostic details;
it reports only whether Django can serve a request.
"""

from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    """Render the initial public landing page."""
    return render(request, "home.html")


def health_check(request):
    """Return a minimal success response without exposing infrastructure state."""
    response = HttpResponse("ok", content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
