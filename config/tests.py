"""Test the foundation's public home and low-information health endpoints."""

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class FoundationPageTests(SimpleTestCase):
    """Verify the minimal public HTTP contract without requiring a database."""

    def test_home_page_returns_success(self):
        """The root route renders the landing page successfully."""
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WBPSC Mock Exam Platform")
        self.assertContains(response, 'name="robots" content="index, follow"')
        self.assertContains(response, '<link rel="canonical" href="http://testserver/">')
        self.assertContains(response, '<meta property="og:title" content="WBPSC Exam Preparation | Free Study Materials and Mock Tests">')
        self.assertContains(response, 'href="/blog/">Blog</a>')

    @override_settings(SOCIAL_LINKS={
        "Facebook": "https://www.facebook.com/example",
        "Instagram": "http://instagram.example/unsafe",
        "Telegram": "javascript:alert(1)",
        "YouTube": "",
    })
    def test_footer_renders_only_configured_https_social_links_safely(self):
        """Only optional HTTPS profiles render, with safe external-link attributes."""
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Follow Us")
        self.assertContains(response, 'href="https://www.facebook.com/example" target="_blank" rel="noopener noreferrer"')
        self.assertNotContains(response, "instagram.example")
        self.assertNotContains(response, "javascript:")

    def test_health_check_is_minimal_and_uncached(self):
        """Health output confirms service availability without database details."""
        response = self.client.get(reverse("health_check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn(b"database", response.content.lower())

    @override_settings(DEBUG=False)
    def test_not_found_page_uses_the_custom_template(self):
        """Production-style 404 responses use the generic branded error page."""
        response = self.client.get("/page-that-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)


class StaticAssetURLTests(TestCase):
    """Verify nested public pages use the root-mounted static URL path."""

    def test_static_assets_use_absolute_root_paths(self):
        """Nginx must be able to serve static files on deeply nested URLs."""
        response = self.client.get(reverse("content:resource_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/static/content/content.css"')
