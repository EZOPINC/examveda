"""Test the foundation's public home and low-information health endpoints."""

from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class FoundationPageTests(SimpleTestCase):
    """Verify the minimal public HTTP contract without requiring a database."""

    def test_home_page_returns_success(self):
        """The root route renders the landing page successfully."""
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WBPSC Mock Exam Platform")

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
