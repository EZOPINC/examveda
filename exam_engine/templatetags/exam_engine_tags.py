"""Expose safe dictionary lookup for per-question result summaries."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Return a mapping entry used to render one attempt response."""
    return mapping.get(key)
