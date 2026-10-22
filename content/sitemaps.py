"""Expose published blog URLs to search crawlers through Django's sitemap view.

The sitemap is intentionally limited to public articles and categories; drafts
and empty categories never become discoverable through this route.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import BlogCategory, ContentPage


class BlogArticleSitemap(Sitemap):
    """List published blog articles and use editorial updates as last modified."""

    changefreq = "monthly"
    priority = 0.7

    def items(self):
        """Return only currently published blog pages."""
        return ContentPage.objects.filter(
            blog_category__isnull=False,
            is_published=True,
            published_at__lte=timezone.now(),
        ).order_by("slug")

    def location(self, item):
        """Return the established stable article route."""
        return reverse("content:blog_detail", args=[item.slug])

    def lastmod(self, item):
        """Return the article's latest edit time for crawler recrawl hints."""
        return item.updated_at


class BlogCategorySitemap(Sitemap):
    """List categories with at least one published article."""

    changefreq = "weekly"
    priority = 0.5

    def items(self):
        """Exclude categories that would resolve to an empty public archive."""
        return BlogCategory.objects.filter(
            articles__is_published=True,
            articles__published_at__lte=timezone.now(),
        ).distinct().order_by("slug")

    def location(self, item):
        """Return the established category archive route."""
        return reverse("content:blog_category", args=[item.slug])
