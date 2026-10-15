"""Verify publication boundaries, canonical URLs and rendered content."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from .models import ContentPage, ExamCategory, ExamStage, ResourceMetadata, Subject, Topic


class ContentPublicationTests(TestCase):
    """Exercise anonymous publication rules and authorized staff preview."""

    @classmethod
    def setUpTestData(cls):
        """Create representative Bengali and English resources for requests."""
        cls.category = ExamCategory.objects.create(name="WBCS", slug="wbcs")
        cls.stage = ExamStage.objects.create(category=cls.category, name="Prelims", slug="prelims")
        cls.subject = Subject.objects.create(name="History", slug="history")
        cls.topic = Topic.objects.create(subject=cls.subject, name="Modern India", slug="modern-india")
        cls.published = ContentPage.objects.create(title="WBCS 2024 Solutions", slug="wbcs-2024-solutions", body="Solution body", language="en", is_published=True, published_at=timezone.now())
        ResourceMetadata.objects.create(page=cls.published, category=cls.category, stage=cls.stage, year=2024, resource_type="solutions", subject=cls.subject, topic=cls.topic)
        cls.draft = ContentPage.objects.create(title="Draft notes", slug="draft-notes", body="Private draft")
        cls.user = get_user_model().objects.create_user(username="editor", password="secure-test-password", is_staff=True, is_superuser=True)

    def test_unpublished_page_is_not_available_through_public_routes(self):
        """Draft slugs must not disclose page content publicly."""
        response = self.client.get(reverse("content:editorial_detail", args=[self.draft.slug]))
        self.assertEqual(response.status_code, 404)

    def test_public_listing_and_canonical_resource_detail_render(self):
        """Published resources appear at the approved archive and detail URLs."""
        listing = self.client.get(reverse("content:type_list", args=["wbcs", "prelims", 2024, "solutions"]))
        detail = self.client.get(reverse("content:resource_detail", args=["wbcs", "prelims", 2024, "solutions", self.published.slug]))
        self.assertContains(listing, "WBCS 2024 Solutions")
        self.assertContains(detail, "Solution body")

    def test_draft_is_visible_only_in_staff_preview(self):
        """Staff can preview a draft while anonymous users cannot."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("content:preview_page", args=[self.draft.pk]))
        self.assertContains(response, "Private draft")
        self.assertContains(response, "not published publicly")

    def test_staff_without_content_permission_cannot_preview(self):
        """Staff status alone does not grant the content view permission."""
        editor = get_user_model().objects.create_user(username="staff-without-content-permission", password="secure-test-password", is_staff=True)
        self.client.force_login(editor)
        response = self.client.get(reverse("content:preview_page", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 403)

    def test_topic_listing_does_not_include_draft_resources(self):
        """Topic archives only contain published resources."""
        response = self.client.get(reverse("content:topic_list", args=["history", "modern-india"]))
        self.assertContains(response, "WBCS 2024 Solutions")
        self.assertNotContains(response, "Draft notes")

    def test_publication_requires_body_and_sets_timestamp(self):
        """Publishing an empty page is rejected and valid publish time is recorded."""
        page = ContentPage(title="Empty", slug="empty", body="", is_published=True)
        with self.assertRaises(ValidationError):
            page.full_clean()
        page.body = "Ready"
        page.full_clean()
        self.assertIsNotNone(page.published_at)


class ContentRouteTests(TestCase):
    """Keep the approved archive and editorial paths stable."""

    def test_archive_and_editorial_url_patterns(self):
        """Reverse canonical public paths without hard-coded view URLs."""
        self.assertEqual(reverse("content:resource_list"), "/free-resources/")
        self.assertEqual(reverse("content:type_list", args=["wbcs", "prelims", 2024, "solutions"]), "/free-resources/wbcs/prelims/2024/solutions/")
        self.assertEqual(reverse("content:editorial_detail", args=["about-exam"]), "/free-resources/pages/about-exam/")


class ContentAdminJourneyTests(TestCase):
    """Exercise editorial creation, preview, publication and withdrawal."""

    def setUp(self):
        """Authenticate as an editor with normal admin content permissions."""
        self.editor = get_user_model().objects.create_superuser(username="admin-editor", email="editor@example.test", password="secure-test-password")
        self.client.force_login(self.editor)

    def test_editor_creates_previews_publishes_and_unpublishes_page(self):
        """Drive the admin add/change forms and confirm public transitions."""
        add_url = reverse("admin:content_contentpage_add")
        response = self.client.post(add_url, {
            "title": "Admin workflow article", "slug": "admin-workflow-article", "summary": "Admin journey", "body": "Draft content",
            "language": "en", "is_published": "", "published_at": "", "seo_title": "", "seo_description": "",
            "created_by": "", "updated_by": "", "_save": "Save",
            "resource-TOTAL_FORMS": "0", "resource-INITIAL_FORMS": "0", "resource-MIN_NUM_FORMS": "0", "resource-MAX_NUM_FORMS": "1",
        })
        self.assertEqual(response.status_code, 302, response.context and response.context[0].get("adminform"))
        page = ContentPage.objects.get(slug="admin-workflow-article")
        self.assertEqual(self.client.get(reverse("content:preview_page", args=[page.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("content:editorial_detail", args=[page.slug])).status_code, 404)

        change_url = reverse("admin:content_contentpage_change", args=[page.pk])
        publish = self.client.post(change_url, {
            "title": page.title, "slug": page.slug, "summary": page.summary, "body": page.body,
            "language": page.language, "is_published": "on", "published_at": "", "seo_title": "", "seo_description": "",
            "created_by": str(self.editor.pk), "updated_by": str(self.editor.pk), "_save": "Save",
            "resource-TOTAL_FORMS": "0", "resource-INITIAL_FORMS": "0", "resource-MIN_NUM_FORMS": "0", "resource-MAX_NUM_FORMS": "1",
        })
        self.assertEqual(publish.status_code, 302)
        page.refresh_from_db()
        self.assertTrue(page.is_published)
        self.assertIsNotNone(page.published_at)
        self.assertEqual(self.client.get(reverse("content:editorial_detail", args=[page.slug])).status_code, 200)

        withdraw = self.client.post(change_url, {
            "title": page.title, "slug": page.slug, "summary": page.summary, "body": page.body,
            "language": page.language, "is_published": "", "published_at": page.published_at.strftime("%Y-%m-%d %H:%M:%S"), "seo_title": "", "seo_description": "",
            "created_by": str(self.editor.pk), "updated_by": str(self.editor.pk), "_save": "Save",
            "resource-TOTAL_FORMS": "0", "resource-INITIAL_FORMS": "0", "resource-MIN_NUM_FORMS": "0", "resource-MAX_NUM_FORMS": "1",
        })
        self.assertEqual(withdraw.status_code, 302)
        self.assertEqual(self.client.get(reverse("content:editorial_detail", args=[page.slug])).status_code, 404)


class ResourceFileAccessTests(TestCase):
    """Keep restricted PDFs inaccessible and public delivery publication-aware."""

    @override_settings(MEDIA_ROOT="")
    def test_file_delivery_requires_public_classification_and_published_page(self):
        """Only public files attached to currently published pages stream."""
        with TemporaryDirectory() as media_dir:
            with self.settings(MEDIA_ROOT=Path(media_dir)):
                category = ExamCategory.objects.create(name="WBCS", slug="wbcs")
                stage = ExamStage.objects.create(category=category, name="Prelims", slug="prelims")
                page = ContentPage.objects.create(title="PDF resource", slug="pdf-resource", body="A PDF", is_published=True, published_at=timezone.now())
                metadata = ResourceMetadata.objects.create(page=page, category=category, stage=stage, year=2024)
                public_file = metadata.files.create(file=SimpleUploadedFile("public.pdf", b"%PDF-1.4 public", content_type="application/pdf"))
                restricted_file = metadata.files.create(file=SimpleUploadedFile("private.pdf", b"%PDF-1.4 private", content_type="application/pdf"), visibility="restricted")
                response = self.client.get(reverse("content:public_file", args=[public_file.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(b"%PDF-1.4 public" in b"".join(response.streaming_content))
                self.assertEqual(self.client.get(reverse("content:public_file", args=[restricted_file.pk])).status_code, 404)
                page.is_published = False
                page.save()
                self.assertEqual(self.client.get(reverse("content:public_file", args=[public_file.pk])).status_code, 404)
