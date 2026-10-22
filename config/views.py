"""Provide foundation HTTP views and shared, validated public social links.

The health endpoint intentionally avoids database probes and diagnostic details;
it reports only whether Django can serve a request. Social profile links are
optional deployment configuration and only HTTPS destinations reach templates.
"""

from urllib.parse import urlsplit

from django.conf import settings
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


def social_links_context(request):
    """Expose only configured HTTPS social profile URLs to shared templates."""
    links = {}
    for name, value in getattr(settings, "SOCIAL_LINKS", {}).items():
        if not value:
            continue
        try:
            parsed = urlsplit(value)
        except ValueError:
            continue
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            links[name] = value
    return {"social_links": links}
